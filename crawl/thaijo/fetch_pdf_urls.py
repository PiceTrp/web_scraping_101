import json
import os
import random
import requests
import logging
import time
from tqdm import tqdm
from playwright.sync_api import sync_playwright
from . import THAIJO_DATA_PATH
from utils.logger import setup_logging
from .utils import get_pdf_links_from_json


SAVE_DIR = os.path.join(THAIJO_DATA_PATH, "pdfs")
RESULTS_FILE = os.path.join(THAIJO_DATA_PATH, "pdf_download_links.json")
LOGGER = setup_logging(
    log_file=os.path.join(THAIJO_DATA_PATH, "scrape_pdf_urls.log"),
    level=logging.DEBUG
)


def load_existing_results():
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_results_to_file(results):
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)


def get_pdf_url_from_fetch(page, url, max_retries=5):
    pdf_urls = []

    def handle_response(response):
        # * track only pdf content
        if "application/pdf" in response.headers.get("content-type", ""):
            pdf_urls.append(response.url)

    page.on("response", handle_response)

    for attempt in range(max_retries):
        try:
            pdf_urls.clear()  # * clear previous attempts
            response = page.goto(url, wait_until="networkidle")
            status = response.status if response else None

            if status == 429:
                wait_time = (2 ** attempt) + random.uniform(1.0, 3.0)
                LOGGER.warning(f"Got 429 on page.goto for {url}. Retrying Round {attempt + 1} in {wait_time:.2f}s...")
                time.sleep(wait_time)
                continue

            # * wait additional time to capture pdf requests triggered by js
            page.wait_for_timeout(5000)

            if pdf_urls:
                LOGGER.debug(f"Captured PDF responses: {pdf_urls}")
                return pdf_urls[0]  # * return the first detected pdf url

            # * optional fallback: extract direct links to pdfs from the dom
            anchors = page.query_selector_all("a[href$='.pdf']")
            if anchors:
                href = anchors[0].get_attribute("href")
                if href:
                    full_url = page.url if href.startswith("http") else page.url.rsplit("/", 1)[0] + "/" + href
                    LOGGER.info(f"[FALLBACK] Found PDF href in DOM: {full_url}")
                    return full_url

            # * no pdf found, retry if not last attempt
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + random.uniform(1.0, 3.0)
                LOGGER.warning(f"No PDF found for {url}. Retrying Round {attempt + 1} in {wait_time:.2f}s...")
                time.sleep(wait_time)
                continue

        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + random.uniform(1.0, 3.0)
                LOGGER.error(f"Error loading {url}: {e}. Retrying Round {attempt + 1} in {wait_time:.2f}s...")
                time.sleep(wait_time)
                continue
            else:
                LOGGER.error(f"[GIVE UP] Failed after {max_retries} attempts due to exception: {e}")
                return None

    LOGGER.error(f"[GIVE UP] Failed to find PDF URL for: {url} after {max_retries} attempts")
    return None


def download_pdf_with_retries(pdf_url, save_dir, max_retries=5):
    os.makedirs(save_dir, exist_ok=True)

    for attempt in range(max_retries):
        try:
            response = requests.get(pdf_url, stream=True, timeout=15)

            if response.status_code == 200:
                basename = pdf_url.split("/")[-1].split("?")[0] or f"file_{int(time.time())}"
                name, ext = os.path.splitext(basename)
                if not ext:
                    ext = ".pdf"
                filepath = os.path.join(save_dir, f"{name}{ext}")

                with open(filepath, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                LOGGER.info(f"[DOWNLOADED] PDF saved to: {filepath}")
                return filepath

            elif response.status_code == 429:
                wait_time = (2 ** attempt) + random.uniform(1.0, 5.0)
                LOGGER.warning(f"[RATE LIMIT] Got 429 for {pdf_url}. Retrying in {wait_time:.2f}s...")
                time.sleep(wait_time)

            else:
                LOGGER.warning(f"[FAILED] HTTP {response.status_code} for {pdf_url}")
                return None

        except Exception as e:
            wait_time = (2 ** attempt) + random.uniform(1.0, 3.0)
            LOGGER.error(f"[ERROR] Download attempt {attempt + 1} failed for {pdf_url}: {str(e)}. Retrying in {wait_time:.2f}s")
            time.sleep(wait_time)

    LOGGER.error(f"[GIVE UP] Failed to download after {max_retries} attempts: {pdf_url}")


def fetch_and_download_pdf_links_from_urls(url_list):
    results = load_existing_results()
    start_time = time.time()

    LOGGER.info(f"Starting PDF extraction for {len(url_list)} URLs.")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        for index, url in tqdm(enumerate(url_list), desc="Processing URLs"):
            LOGGER.info(f"================= [ITEM] Process item index: {index} ================= ")

            if url in results and results[url] is not None:
                LOGGER.info(f"[SKIP] Already processed: {url}")
                LOGGER.info(f"================= [ITEM] Finished item index: {index} ================= ")
                continue

            LOGGER.info(f"[START] Fetching PDF from: {url}")
            try:
                pdf_url = get_pdf_url_from_fetch(page, url, max_retries=5)
            except Exception as e:
                LOGGER.error(f"[ERROR] Exception while processing {url}: {str(e)}")
                pdf_url = None

            if pdf_url:
                LOGGER.info(f"[SUCCESS] Found PDF: {pdf_url}")
                # Download from pdf_url
                download_pdf_with_retries(pdf_url, save_dir=SAVE_DIR, max_retries=5)
            else:
                LOGGER.warning(f"[FAILED] No PDF found at: {url}")
            
            # save metadata to json file
            results[url] = pdf_url
            save_results_to_file(results)
            LOGGER.info(f"[SAVED] Updated results to JSON.")

            LOGGER.info(f"================= [ITEM] Finished item index: {index} ================= ")

        browser.close()

    elapsed = time.time() - start_time
    LOGGER.info(f"Completed processing {len(url_list)} URLs in {elapsed:.2f} seconds.")
    LOGGER.info(f"Total PDFs found: {sum(1 for v in results.values() if v)}")

    return results


def main():
    # step 4: get all scraped pdf links
    urls = get_pdf_links_from_json(os.path.join(THAIJO_DATA_PATH, "thaijo_pdf_links.json"))

    # step 4: get all scraped pdf links
    pdf_links = fetch_and_download_pdf_links_from_urls(urls[:2000])

    print("\n=== Summary ===")
    for source_url, pdf_url in pdf_links.items():
        print(f"{source_url} → {pdf_url}")
    print("=== End ===")

if __name__ == "__main__":
    main()