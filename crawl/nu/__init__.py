import os
import logging
from utils.logger import setup_logging

# __file__ points to current file
CURRENT_FILE = os.path.abspath(__file__)

# crawl/thaijo/__init__.py -> project root: ../../..
ROOT_PATH = os.path.abspath(os.path.join(CURRENT_FILE, "../../../"))
CRAWL_PATH = os.path.join(ROOT_PATH, 'crawl')
DATA_PATH = os.path.join(ROOT_PATH, 'data')
NU_DATA_PATH = os.path.join(DATA_PATH, 'nu')
PDF_SAVE_DIR = os.path.join(NU_DATA_PATH, "pdfs")
METADATA_JSON_PATH = os.path.join(NU_DATA_PATH, "metadata.json")

# Ensure log and save directory exists
os.makedirs(NU_DATA_PATH, exist_ok=True)
os.makedirs(PDF_SAVE_DIR, exist_ok=True)

# Setup logger for the package
LOGGER = setup_logging(
    log_file=os.path.join(NU_DATA_PATH, "ku_scrape.log"),
    level=logging.DEBUG
)

# Optional: define __all__ if other modules will use `from . import *`
__all__ = ["ROOT_PATH", "CRAWL_PATH", "DATA_PATH", "NU_DATA_PATH", "LOGGER"]
