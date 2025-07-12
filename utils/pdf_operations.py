import requests
import os
import shutil
import pandas as pd
from tqdm import tqdm
from .logger import LOGGER


def check_pdf_downloadable(urls):
    """
    Checks if a list of URLs are likely to be downloadable PDFs by 
    verifying the content type and performing a HEAD request.

    Args:
        urls (list): A list of URLs to check.

    Returns:
        list: A list of URLs that are likely downloadable PDFs.
    """

    downloadable_pdfs = []
    LOGGER.info(f"Starting check for downloadable PDFs on {len(urls)} URLs.")
    for url in tqdm(urls, desc="Checking PDF URLs"):
        try:
            # Perform a HEAD request to get headers without downloading the whole file
            response = requests.head(url, allow_redirects=True, timeout=5)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

            content_type = response.headers.get('Content-Type', '')
            # Check if content type indicates a PDF (case-insensitive)
            if 'pdf' in content_type.lower():
                downloadable_pdfs.append(url)
                LOGGER.info(f"Found PDF: {url}")
            else:
                LOGGER.debug(f"Skipping: {url} - Content-Type is not PDF: {content_type}")

        except requests.exceptions.RequestException as e:
            LOGGER.warning(f"Error checking {url}: {e}")  # Use warning for network errors
        except Exception as e:
            LOGGER.error(f"An unexpected error occurred while checking {url}: {e}")

    LOGGER.info(f"Finished PDF check. Found {len(downloadable_pdfs)} downloadable PDFs.")
    return downloadable_pdfs


def download_pdfs(urls, download_folder):
    """
    Downloads PDF files from a list of URLs and saves them to a specified folder.

    Args:
        urls (list): A list of URLs of PDF files to download.
        download_folder (str): The path to the folder where PDFs should be saved.
    """

    LOGGER.info(f"Starting PDF download to folder: {download_folder}")
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)
        LOGGER.info(f"Created download folder: {download_folder}")

    for url in tqdm(urls, desc="Downloading PDFs"):
        try:
            # Extract filename from URL or generate one if not available
            filename = url.split('/')[-1] if url.split('/')[-1] else "downloaded_pdf"
            if not filename.endswith(".pdf"):
                filename += ".pdf"

            filepath = os.path.join(download_folder, filename)

            # Check if the file already exists, skip if it does
            if os.path.exists(filepath):
                LOGGER.info(f"Skipping download: {filename} already exists at {filepath}.")
                continue

            # Use streaming to handle potentially large files efficiently
            with requests.get(url, stream=True, allow_redirects=True, timeout=10) as r:
                r.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
                # Save the PDF file
                with open(filepath, 'wb') as f:
                    shutil.copyfileobj(r.raw, f)
                LOGGER.info(f"Downloaded: {filename} from {url}")

        except requests.exceptions.RequestException as e:
            LOGGER.warning(f"Error downloading {url}: {e}")
        except OSError as e:
            LOGGER.error(f"Error saving {filename} from {url}: {e}")
        except Exception as e:
            LOGGER.error(f"An unexpected error occurred while handling {url}: {e}")
    
    LOGGER.info(f"Finished PDF download for {len(urls)} URLs.")


def retrieve_unique_urls(data_folder: str):
    """
    Retrieves unique URLs from text and Excel files within a specified folder.

    This function scans a directory for files with '.txt' and '.xlsx' extensions.
    From text files, it reads each line as a URL.
    From Excel files, it reads the first column (assumed to be named 'url') 
    and extracts URLs.

    Args:
        data_folder (str): The path to the folder containing the data files.

    Returns:
        set: A set of unique URLs found across all specified files.
    """

    unique_urls = set()
    LOGGER.info(f"Starting URL retrieval from folder: {data_folder}")

    if not os.path.exists(data_folder):
        LOGGER.error(f"Data folder not found: {data_folder}")
        return unique_urls

    for filename in tqdm(os.listdir(data_folder), desc="Retrieving URLs"):
        filepath = os.path.join(data_folder, filename)

        if filename.endswith(".txt"):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        url = line.strip()  # Remove leading/trailing whitespace
                        if url:  # Ensure the line is not empty
                            unique_urls.add(url)
                LOGGER.info(f"Processed text file: {filename}")
            except Exception as e:
                LOGGER.error(f"Error reading text file {filename}: {e}. Skipping.")

        elif filename.endswith(".xlsx"):
            try:
                df = pd.read_excel(filepath)
                # Assuming the first column contains URLs
                if not df.empty and 'url' in df.columns:  # Check if 'url' column exists
                    for url in df['url'].dropna().astype(str):  # Handle potential NaNs and ensure string type
                        if url:
                            unique_urls.add(url.strip())
                    LOGGER.info(f"Processed Excel file: {filename}")
                else:
                    LOGGER.warning(f"No 'url' column or empty sheet in {filename}. Skipping.")
            except Exception as e:
                LOGGER.error(f"Error reading Excel file {filename}: {e}. Skipping.")
        else:
            LOGGER.debug(f"Skipping non-txt/xlsx file: {filename}")

    LOGGER.info(f"Finished URL retrieval. Found {len(unique_urls)} unique URLs.")
    return unique_urls