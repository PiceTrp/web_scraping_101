import os
from typing import List, Dict, Any
from contextlib import contextmanager
import time
from serpapi import GoogleSearch
from utils.logger import LOGGER


@contextmanager
def timing(description=""):
    start = time.time()
    yield
    end = time.time()
    print(f"{description} took {end - start:.2f} seconds")


class SerpapiScraper:
    def __init__(self, serpapi_key=None):
        """
        Initialize the SerpapiScraper with an optional SerpAPI key.
        """
        self.serpapi_key = os.getenv("SERPAPI_API_KEY")

    def fetch_from_query(self, query, num=10, start=0) -> Dict:
        try:
            params = {
                "engine": "google",
                "q": query,
                "api_key": self.serpapi_key,
                # "location": "Thailand",
                # "gl": "th",
                # "hl": "th",
                "num": num, # num per page
                "start": start
            }
            LOGGER.debug(f"Sending request to SerpAPI with params: {params}")
            search = GoogleSearch(params)
            results = search.get_dict()
            return results
        except Exception as e:
            LOGGER.error(f"Error while fetching from SerpAPI at start={start}: {e}")
            return None
        
    def scrape(self, query: str = "search query") -> List[Any]:
        # setting up serpapi
        # query = "site:innodev.moe.go.th filetype:pdf"
        num = 100
        start = 0

        # fetch all data
        results = []
        while True:
            with timing(f"⏱️ Fetching data (start={start})"):
                page_data = self.fetch_from_query(query, num=num, start=start)

            if not page_data:
                LOGGER.warning(f"⚠️  Empty response or error occurred at start={start}. Stopping.")
                break

            organic_results = page_data.get("organic_results", [])
            if not organic_results:
                LOGGER.info(f"✅ No more organic results at start={start}. Ending loop.")
                break

            LOGGER.info(f"✅ Retrieved {len(organic_results)} results at start={start}")
            results.append(page_data)

            # keep going next page, until all
            start += num
        
        return results