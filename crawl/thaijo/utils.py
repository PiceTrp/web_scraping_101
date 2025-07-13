import os
import shutil
import random
import time
import requests
from tqdm import tqdm
import json
from typing import List, Dict
import re
from utils.logger import setup_logging
from . import *


def extract_markdown_from_h2(input_filepath: str, target_h2_text: str) -> str:
    """
    Reads a Markdown file, finds the specified H2 tag, and saves all content
    from that H2 tag to the end of the file into a new output file.

    Args:
        input_filepath (str): The path to the input Markdown file.
        target_h2_text (str): The exact text of the H2 tag to search for.
                              (e.g., "วารสารทั้งหมด" for "## วารสารทั้งหมด")
    """
    try:
        # Ensure the input file exists
        if not os.path.exists(input_filepath):
            print(f"Error: Input file not found at '{input_filepath}'")
            return

        # Read the entire content of the input Markdown file
        with open(input_filepath, "r", encoding="utf-8") as file:
            content = file.read()

        # Construct the Markdown H2 tag pattern to search for
        # We use a regex to be flexible with spaces after '##'
        # re.escape is used to escape any special characters in the target_h2_text
        import re
        search_pattern = re.compile(r'^##\s*' + re.escape(target_h2_text) + r'\s*$', re.MULTILINE)

        # Search for the target H2 tag
        match = search_pattern.search(content)

        if match:
            # Get the starting index of the matched H2 tag
            start_index = match.start()
            # Extract content from the start_index to the end of the file
            extracted_content = content[start_index:]
            return extracted_content
        else:
            LOGGER.warning(f"Warning: H2 tag with text '{target_h2_text}' not found in '{input_filepath}'. No content saved.")
            return 
    except Exception as e:
        LOGGER.error(f"An error occurred: {e}")


def extract_markdown_links_as_json(markdown_text: str) -> List[Dict[str, str]]:
    """
    Extracts all Markdown-style links with optional titles from a string
    and returns them as a list of {label: url} dictionaries.

    Args:
        markdown_text (str): The markdown content as a string.

    Returns:
        List[Dict[str, str]]: A list of label-URL pairs as dictionaries.
    """
    # Match pattern: [label](url "title")
    pattern = re.compile(r'\[\s*(.*?)\s*\]\(\s*(\S+)(?:\s+"(.*?)")?\s*\)')
    
    matches = pattern.findall(markdown_text)
    
    # Return as list of dicts: {label: url}
    return [{label: url} for label, url, _ in matches]


def extract_pdf_links_from_markdown(markdown_text: str) -> List[str]:
    """
    Extract all PDF links from markdown-formatted text.

    Args:
        markdown_text (str): Markdown content containing links.

    Returns:
        List[str]: List of URLs pointing to PDF files (anchor text contains 'PDF').
    """
    if not isinstance(markdown_text, str):
        raise ValueError("Input must be a string")

    # Regex pattern to match markdown links: [text](url)
    pattern = re.compile(r'\[([^\]]*pdf[^\]]*)\]\((https?://[^\)]+)\)', re.IGNORECASE)

    matches = pattern.findall(markdown_text)
    pdf_links = [url for _, url in matches]

    return pdf_links


def get_pdf_links_from_json(json_file: str) -> list[str]:
    """
    Loads a JSON result file and extracts all PDF links into a flat list.

    Args:
        json_file (str): Path to the JSON file.

    Returns:
        list[str]: A flat list of all PDF URLs.
    """
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    all_links = []
    for item in data.values():
        all_links.extend(item.get("links", []))

    return all_links


# def check_pdf_downloadable(urls, verify_pdf_header=True):
#     """
#     Checks if a list of URLs are likely to be downloadable PDFs by verifying
#     the Content-Type header and optionally validating the PDF header bytes.

#     Args:
#         urls (list): A list of URLs to check.
#         verify_pdf_header (bool): If True, performs a small read to confirm PDF header bytes.

#     Returns:
#         list: A list of URLs that are likely downloadable PDFs.
#     """
#     downloadable_pdfs = []
#     LOGGER.info(f"Starting check for downloadable PDFs on {len(urls)} URLs.")

#     for url in tqdm(urls, desc="Checking PDF URLs"):
#         LOGGER.info(f"Checking: {url}")
#         try:
#             with requests.get(url, stream=True, allow_redirects=True, timeout=10) as response:
#                 response.raise_for_status()

#                 content_type = response.headers.get('Content-Type', '').lower()

#                 # Basic check via Content-Type header
#                 if 'pdf' in content_type:
#                     downloadable_pdfs.append(url)
#                     LOGGER.info(f"✅ Found PDF by Content-Type: {url}")
#                     continue

#                 # Optionally verify PDF header bytes if content-type is ambiguous
#                 if verify_pdf_header:
#                     chunk = response.raw.read(5)  # Read first 5 bytes to check PDF header "%PDF-"
#                     if chunk.startswith(b'%PDF'):
#                         downloadable_pdfs.append(url)
#                         LOGGER.info(f"✅ Found PDF by header bytes: {url}")
#                     else:
#                         LOGGER.debug(f"⛔ Skipped: {url} - Not a PDF by header bytes")
#                 else:
#                     LOGGER.debug(f"⛔ Skipped: {url} - Content-Type: {content_type}")

#         except requests.exceptions.RequestException as e:
#             LOGGER.warning(f"⚠️ Error checking {url}: {e}")
#         except Exception as e:
#             LOGGER.error(f"❌ Unexpected error while checking {url}: {e}")

#     LOGGER.info(f"Finished PDF check. Found {len(downloadable_pdfs)} downloadable PDFs.")
#     return downloadable_pdfs


# def download_pdfs(urls, download_folder, max_retries=5):
#     LOGGER.info(f"Starting PDF download to folder: {download_folder}")
    
#     if not os.path.exists(download_folder):
#         os.makedirs(download_folder)
#         LOGGER.info(f"Created download folder: {download_folder}")

#     for i, url in enumerate(tqdm(urls, desc="Downloading PDFs")):
#         retries = 0
#         while retries < max_retries:
#             try:
#                 LOGGER.info(f"[{i+1}/{len(urls)}] Downloading: {url}")
#                 with requests.get(url, stream=True, allow_redirects=True, timeout=10) as r:
#                     if r.status_code == 429:
#                         raise requests.exceptions.HTTPError("429 Too Many Requests")

#                     r.raise_for_status()

#                     # Extract filename
#                     cd = r.headers.get('Content-Disposition')
#                     filename = None
#                     if cd:
#                         fname_match = re.findall('filename="?([^\'";]+)"?', cd)
#                         if fname_match:
#                             filename = fname_match[0]

#                     if not filename:
#                         filename = url.split('/')[-1]
#                         if not filename or '?' in filename:
#                             filename = f"downloaded_{i+1}.pdf"

#                     if not filename.lower().endswith('.pdf'):
#                         filename += ".pdf"

#                     filepath = os.path.join(download_folder, filename)

#                     if os.path.exists(filepath):
#                         LOGGER.info(f"Skipping download: {filename} already exists.")
#                         break

#                     # Save the file
#                     with open(filepath, 'wb') as f:
#                         shutil.copyfileobj(r.raw, f)

#                     # Validate PDF
#                     with open(filepath, 'rb') as f:
#                         header = f.read(4)
#                         if header != b'%PDF':
#                             LOGGER.warning(f"File {filename} does not appear to be a valid PDF.")

#                     LOGGER.info(f"✅ Downloaded: {filename}")
#                     break  # Exit retry loop on success

#             except requests.exceptions.HTTPError as e:
#                 if "429" in str(e):
#                     wait_time = 2 ** retries + random.uniform(1, 3)  # backoff + jitter
#                     LOGGER.warning(f"429 Too Many Requests — Retrying in {wait_time:.2f}s...")
#                     time.sleep(wait_time)
#                     retries += 1
#                     continue
#                 else:
#                     LOGGER.warning(f"HTTP error for {url}: {e}")
#                     break
#             except requests.exceptions.RequestException as e:
#                 LOGGER.warning(f"Network error for {url}: {e}")
#                 retries += 1
#                 time.sleep(1.5 + random.uniform(0, 2))
#             except OSError as e:
#                 LOGGER.error(f"File write error for {url}: {e}")
#                 break
#             except Exception as e:
#                 LOGGER.error(f"Unexpected error for {url}: {e}")
#                 break

#         else:
#             LOGGER.error(f"❌ Failed after {max_retries} retries: {url}")

#         # Always sleep a little between downloads
#         time.sleep(random.uniform(1.5, 4))

#     LOGGER.info(f"Finished PDF download for {len(urls)} URLs.")

