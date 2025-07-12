import os
import argparse
from crawl.serpapi_scraper import SerpapiScraper
from utils.pdf_operations import check_pdf_downloadable, download_pdfs
from utils.logger import LOGGER


class PDFScraper(SerpapiScraper):
    def __init__(self, data_name: str = "website_name", domain_name: str = "website_domain_name"):
        super().__init__()
        self.root_dir = os.getcwd()
        self.data_dir = os.path.join(self.root_dir, 'data', data_name)
        self.pdf_download_dir = os.path.join(self.data_dir, 'pdfs')
        self.data_name = data_name # example: innodev
        self.domain_name = domain_name # example: innodev.moe.go.th

    def scrape_pdfs(self) -> None:
        search_term = f"site:{self.domain_name} filetype:pdf"
        scraped_data = super().scrape(query=search_term)
        # get pdf urls
        pdf_urls = []
        for response in scraped_data:
            for result in response.get("organic_results", []):
                link = result.get("link", "")
                if link.lower().endswith(".pdf"):
                    pdf_urls.append(link)
        LOGGER.info(f"Found {len(pdf_urls)} PDF urls.")

        # Check if URLs are downloadable PDFs
        valid_pdf_urls = check_pdf_downloadable(pdf_urls) # Convert set to list for tqdm
        LOGGER.info("\n--- Downloadable PDF URLs Summary ---")
        for url in sorted(valid_pdf_urls):
            LOGGER.info(url)

        # Download the PDFs
        LOGGER.info(f"PDFs will be downloaded to: {self.pdf_download_dir}")
        download_pdfs(urls=valid_pdf_urls, download_folder=self.pdf_download_dir)

        LOGGER.info(f"\nTotal Downloadable PDF URLs Found: {len(valid_pdf_urls)}")
        LOGGER.info("Script finished.")


def parse_args():
    parser = argparse.ArgumentParser(description="PDF Scraper using SerpAPI")

    parser.add_argument(
        "--data_name", 
        type=str, 
        default="source", 
        help="Name to save data under (used as folder name)"
    )

    parser.add_argument(
        "--domain_name", 
        type=str, 
        default="source.co.th", 
        help="Domain name to scrape (e.g., innodev.moe.go.th)"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    LOGGER.info(f"🚀 Starting PDF scraping for domain: {args.domain_name}")
    
    scraper = PDFScraper(data_name=args.data_name, domain_name=args.domain_name)
    scraper.scrape_pdfs()

    LOGGER.info("✅ PDF scraping completed successfully.")

if __name__ == "__main__":
    main()

# use case
# uv run crawl/pdf_scraper.py --data_name innodev --domain_name innodev.moe.go.th