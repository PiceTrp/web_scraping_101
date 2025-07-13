import os
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode, BrowserConfig
from . import THAIJO_DATA_PATH, LOGGER



# ======================== STILL NOT WORKING ========================
# ======================== STILL NOT WORKING ========================
# ======================== STILL NOT WORKING ========================



URL = "https://he01.tci-thaijo.org/index.php/crmjournal/article/view/275362/186873"
downloads_path = os.path.join(THAIJO_DATA_PATH, "my_downloads")  # Custom download path
os.makedirs(downloads_path, exist_ok=True)


async def main():
    browser_config = BrowserConfig(
        headless=False, 
        viewport_width=1280, 
        viewport_height=720,
        accept_downloads=True,
        downloads_path=downloads_path)

    js_commands = """
        const button = document.querySelector('button.toolbarButton.download.hiddenMediumView');
        if (button) {
            button.click();
        }
    """

    js_wait_for_condition = """
        js:() => {
            // Select the specific <span> element inside the download button
            const downloadSpan = document.querySelector('button#download span[data-l10n-id="download_label"]');

            // Check if the element exists AND if its text content, trimmed of whitespace, is "Download"
            return downloadSpan && downloadSpan.textContent.trim() === 'Download';
        }
    """

    # js_wait_for_condition = """
    #     js:() => {
    #         if (!window.startTime) {
    #             window.startTime = Date.now();
    #             return false;
    #         }
    #         return Date.now() - window.startTime >= 10000;
    #     }
    # """

    crawler_config = CrawlerRunConfig(
        js_code=js_commands,
        wait_for=js_wait_for_condition,  # Wait 10 seconds for the download to start
        cache_mode=CacheMode.BYPASS,
        session_id="my_session",
    )

    initial_config = CrawlerRunConfig(
        session_id="my_session",
        cache_mode=CacheMode.BYPASS,
    )
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=URL,
                                    config=initial_config)
        
        # Keep the browser open manually (optional debugging pause)
        await asyncio.sleep(10)  # keep open for n seconds
        
        print("\nAttempting to click download button and wait for specific content...")
        click_button_result = await crawler.arun(
            url=URL,  # Another pass
            config=crawler_config,
        )

    if click_button_result.downloaded_files:
        print("Downloaded files:")
        for file_path in click_button_result.downloaded_files:
            print(f"- {file_path}")
            file_size = os.path.getsize(file_path)
            print(f"- File size: {file_size} bytes")
    else:
        print("No files downloaded.")
        
if __name__ == "__main__":
    asyncio.run(main())
