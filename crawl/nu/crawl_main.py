import os
import json
from tqdm import tqdm
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig
from . import LOGGER
import re
from typing import List, Optional, Dict
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import random
import time
import datetime
from . import LOGGER, PDF_SAVE_DIR, METADATA_JSON_PATH


def load_existing_results():
    if os.path.exists(METADATA_JSON_PATH):
        with open(METADATA_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_results(results):
    with open(METADATA_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)


def download_pdf_with_retries(
    pdf_download_url: str, 
    save_dir: str, 
    max_retries: int = 5,
    timeout: int = 30,
    chunk_size: int = 8192
) -> Optional[str]:
    """
    Download PDF with exponential backoff retry logic and robust error handling.
    
    Args:
        pdf_download_url: URL to download PDF from
        save_dir: Directory to save the file
        max_retries: Maximum number of retry attempts
        timeout: Request timeout in seconds
        chunk_size: Size of chunks for streaming download
    
    Returns:
        str: Filepath if successful, None if failed
    """
    
    # * create directory if it doesn't exist
    os.makedirs(save_dir, exist_ok=True)
    
    # * create session with connection pooling and retry strategy
    session = requests.Session()
    retry_strategy = Retry(
        total=0,  # * we handle retries manually for better control
        backoff_factor=0,
        status_forcelist=[500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # * set headers to appear more like a browser
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    
    try:
        for attempt in range(max_retries):
            try:
                LOGGER.info(f"[ATTEMPT {attempt + 1}/{max_retries}] Downloading: {pdf_download_url}")
                
                # * make request with streaming
                response = session.get(
                    pdf_download_url, 
                    stream=True, 
                    timeout=timeout,
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    # * verify content type
                    content_type = response.headers.get('content-type', '').lower()
                    if 'pdf' not in content_type and 'application/pdf' not in content_type:
                        LOGGER.warning(f"[WARNING] Content type may not be PDF: {content_type}")
                    
                    # * generate filename with better logic
                    basename = pdf_download_url.split("/")[-1].split("?")[0]
                    if not basename:
                        basename = f"file_{int(time.time())}"
                    
                    name, ext = os.path.splitext(basename)
                    if not ext or ext.lower() != '.pdf':
                        ext = ".pdf"
                    
                    # * add timestamp to avoid conflicts
                    max_name_length = 100  # avoid file name too long error
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{name[:max_name_length]}_{timestamp}{ext}"
                    filepath = os.path.join(save_dir, filename)
                    
                    # * download with progress tracking
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded_size = 0
                    
                    with open(filepath, "wb") as f:
                        for chunk in response.iter_content(chunk_size=chunk_size):
                            if chunk:  # * filter out keep-alive chunks
                                f.write(chunk)
                                downloaded_size += len(chunk)
                                
                                # * log progress for large files
                                if total_size > 0 and downloaded_size % (chunk_size * 100) == 0:
                                    progress = (downloaded_size / total_size) * 100
                                    LOGGER.debug(f"[PROGRESS] {progress:.1f}% downloaded")
                    
                    # * verify file was created and has content
                    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                        LOGGER.info(f"[SUCCESS] PDF saved to: {filepath}")
                        return filepath
                    else:
                        LOGGER.error(f"[ERROR] File creation failed or file is empty: {filepath}")
                        if os.path.exists(filepath):
                            os.remove(filepath)  # * cleanup empty file
                        continue
                
                elif response.status_code == 429:
                    # * rate limiting - exponential backoff with jitter
                    wait_time = (2 ** attempt) + random.uniform(1.0, 5.0)
                    LOGGER.warning(f"[RATE LIMIT] Got 429. Retrying in {wait_time:.2f}s...")
                    time.sleep(wait_time)
                    continue
                
                elif response.status_code in [403, 404]:
                    # * client errors - don't retry
                    LOGGER.error(f"[CLIENT ERROR] HTTP {response.status_code} - not retrying: {pdf_download_url}")
                    return None
                
                elif response.status_code >= 500:
                    # * server errors - retry with backoff
                    wait_time = (2 ** attempt) + random.uniform(1.0, 3.0)
                    LOGGER.warning(f"[SERVER ERROR] HTTP {response.status_code}. Retrying in {wait_time:.2f}s...")
                    time.sleep(wait_time)
                    continue
                
                else:
                    # * other status codes
                    LOGGER.warning(f"[UNEXPECTED] HTTP {response.status_code} for {pdf_download_url}")
                    wait_time = (2 ** attempt) + random.uniform(1.0, 3.0)
                    time.sleep(wait_time)
                    continue
                    
            except requests.exceptions.Timeout:
                wait_time = (2 ** attempt) + random.uniform(1.0, 3.0)
                LOGGER.error(f"[TIMEOUT] Request timed out. Retrying in {wait_time:.2f}s...")
                time.sleep(wait_time)
                
            except requests.exceptions.ConnectionError:
                wait_time = (2 ** attempt) + random.uniform(1.0, 3.0)
                LOGGER.error(f"[CONNECTION ERROR] Network issue. Retrying in {wait_time:.2f}s...")
                time.sleep(wait_time)
                
            except requests.exceptions.RequestException as e:
                wait_time = (2 ** attempt) + random.uniform(1.0, 3.0)
                LOGGER.error(f"[REQUEST ERROR] {str(e)}. Retrying in {wait_time:.2f}s...")
                time.sleep(wait_time)
                
            except Exception as e:
                wait_time = (2 ** attempt) + random.uniform(1.0, 3.0)
                LOGGER.error(f"[UNEXPECTED ERROR] {str(e)}. Retrying in {wait_time:.2f}s...")
                time.sleep(wait_time)
    
    finally:
        # * cleanup session
        session.close()
    
    LOGGER.error(f"[GIVE UP] Failed to download after {max_retries} attempts: {pdf_download_url}")
    return None


def extract_pdf_links_with_label_check(markdown_content: str) -> List[Dict]:
    """
    Extracts markdown links where both the label and the href contain '.pdf'.

    Args:
        markdown_content (str): The markdown string to search.

    Returns:
        List[Dict]: A list of dictionaries with 'text' and 'download_url'.
    """
    pattern = r'\*?\s*\[([^\]]*\.pdf[^\]]*)\]\((https?://[^\s\)]*\.pdf)[^\)]*\)'

    matches = re.findall(pattern, markdown_content)
    
    extracted_links = []
    for link_text, url in matches:
        extracted_links.append({
            'text': link_text.strip(),
            'download_url': url
        })

    return extracted_links


async def crawl_webpage(url: str, verbose: bool = False):
    browser_config = BrowserConfig(
        headless=True, # set to False for debugging | show browser
        verbose=False,
    )
    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            # * crawl the webpage
            result = await crawler.arun(url=url)
            if result.success:
                LOGGER.info(f"✅ Result Length: {len(result.cleaned_html)}")
                if verbose:
                    LOGGER.info("\n ======= Preview all the content =======\n")
                    LOGGER.info(f"{result.markdown}\n")
            return result.markdown
    except Exception as e:
        LOGGER.error(f"[CRAWL ERROR] Unexpected error in crawl_webpage: {str(e)}")
        return None


def get_download_links(result_markdown: str):
    LOGGER.info("[LINK EXTRACTION] Searching for download links...")
    links_to_download = extract_pdf_links_with_label_check(result_markdown)
    if not links_to_download:
        LOGGER.warning("[NO LINKS] No download links found in content")
        return None

    # * log found links
    for i, link_data in enumerate(links_to_download):
        LOGGER.info(f"[LINK {i+1}] Text: '{link_data['text']}' | URL: {link_data['download_url']}")
    
    return links_to_download


async def crawl_and_download_pdf(url: str) -> List[str]:
    result_markdown = await crawl_webpage(url)
    if not result_markdown:
        return None
    
    links_to_download = get_download_links(result_markdown)
    if not links_to_download:
        return None
    
    # * download files
    downloaded_files = []
    for i, link_data in enumerate(links_to_download):
        try:
            LOGGER.info(f"[DOWNLOAD START] Downloading file {i+1}/{len(links_to_download)}")
            
            filepath = download_pdf_with_retries(
                pdf_download_url=link_data["download_url"],
                save_dir=PDF_SAVE_DIR,
            )
            
            if filepath:
                downloaded_files.append(filepath)
                LOGGER.info(f"[DOWNLOAD SUCCESS] File saved: {filepath}")
            else:
                LOGGER.error(f"[DOWNLOAD FAILURE] Failed to download: {link_data['download_url']}")
                
        except Exception as e:
            LOGGER.error(f"[DOWNLOAD EXCEPTION] Error downloading {link_data['download_url']}: {str(e)}")
            continue
    
    # * return result
    if downloaded_files:
        LOGGER.info(f"[OPERATION SUCCESS] Downloaded {len(downloaded_files)} file(s)")
        metadata = {"source_url": url, 
                    "download_url": links_to_download, 
                    "downloaded_filename": [os.path.basename(f) for f in downloaded_files]}
        return metadata
    else:
        LOGGER.error("[OPERATION FAILURE] No files were downloaded successfully")
        return None


async def main():
    MAX_ID = 1000
    results = load_existing_results()

    for index in tqdm(range(1, MAX_ID)):
        # our target url to each ku webpage
        target_url = f"https://nuir.lib.nu.ac.th/dspace/handle/123456789/{index}"

        # skip already processed
        if str(index) in results: # JSON keys are strings
            LOGGER.info(f"[SKIP] Already processed index: {index}, url: {target_url}")
            LOGGER.info(f"================= [ITEM] Finished item index: {index} ================= ")
            continue

        # crawl and download pdf
        LOGGER.info(f"[START] start crawling {target_url}")
        metadata = await crawl_and_download_pdf(target_url)

        if metadata:
            results[index] = metadata
            # Save after each successful download
            save_results(results)
            LOGGER.info(f"[LOG] Updated results to JSON.")
        else:
            metadata = {"source_url": target_url, 
                        "download_url": None, 
                        "downloaded_filename": None}
            results[index] = metadata
            save_results(results)
            LOGGER.info(f"[LOG] Updated None results to JSON.")


if __name__ == "__main__":
   asyncio.run(main())