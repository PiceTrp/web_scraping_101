import os
import json
from tqdm import tqdm
from typing import List, Dict
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode, BrowserConfig
from . import THAIJO_DATA_PATH, LOGGER
from .utils import extract_markdown_from_h2, extract_markdown_links_as_json, extract_pdf_links_from_markdown, get_pdf_links_from_json, check_pdf_downloadable, download_pdfs


URL = "https://www.tci-thaijo.org/"


async def crawl_thaijo():
    session_id = "thaijo_session"

    browser_config = BrowserConfig(
        headless=False, # visible for demonstration
        viewport_width=1280,
        viewport_height=720,
        verbose=True,
    )

    initial_config = CrawlerRunConfig(
        session_id=session_id,
        cache_mode=CacheMode.BYPASS,
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        # Step 1: Load webpage
        result = await crawler.arun(
            url=URL,  # Another pass
            config=initial_config,
        )

        print("✅ HTML Length After Click:", len(result.cleaned_html))
        print("\n ======= Markdown Preview =======\n")
        print(result.markdown)

        # Step 2: scroll down and click button to toggle magazine content
        click_button_js_commands = """
            window.scrollTo(0, document.body.scrollHeight);
            const button = document.querySelector('button.v-btn.v-btn--flat.v-btn--text');
            if (button) {
                // Simulate a click event on the button
                button.click();
                console.log('Button clicked successfully!');
            } else {
                console.log('Button not found. Please ensure the button exists in the DOM with the specified classes.');
            }
        """
        click_button_wait_for_condition = """
            js:() => {
                const items = document.querySelectorAll('ul[data-v-82de9d82] li[data-v-82de9d82]');
                return items.length >= 30;
            }
        """

        click_button_config = CrawlerRunConfig(
            js_code=click_button_js_commands,
            wait_for=click_button_wait_for_condition,
            js_only=True, 
            # Mark that we do not re-navigate, but run JS in the same session:
            session_id=session_id,
            cache_mode=CacheMode.BYPASS,
        )

        print("\nAttempting to click button and wait for specific content...")
        click_button_result = await crawler.arun(
            url=URL,  # Another pass
            config=click_button_config,
        )

        print("✅ Scrape result HTML Length After Click and Wait:", len(click_button_result.cleaned_html))
        print("\n ======= Markdown Preview (After Click and Wait) =======\n")
        print(click_button_result.markdown)

        # Keep the browser open manually (optional debugging pause)
        await asyncio.sleep(5)  # keep open for n seconds

    # save markdown result
    save_md_path = f"{THAIJO_DATA_PATH}/thaijo_markdown.md"
    with open(save_md_path, "w", encoding="utf-8") as f:
        f.write(click_button_result.markdown)
        print(f"✅ Save scraping result to {save_md_path}")


async def cralw_pdf_links(web_urls: List[Dict], headless=True): # example: [{"Source A": "https://source-a.com"}]

    browser_config = BrowserConfig(
        headless=headless, # set to False for debugging | show browser
        viewport_width=1280,
        viewport_height=720,
        verbose=False,
    )

    results = {}
    
    for i, item in tqdm(enumerate(web_urls)):
        
        source_name, source_url = list(item.items())[0]
        LOGGER.info(f"source name: {source_name}, source_url: {source_url}")
        LOGGER.info("Start crawling ...")

        crawler_config = CrawlerRunConfig(
            session_id=source_name,
            cache_mode=CacheMode.BYPASS,
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:
            # Scrape webpage
            result = await crawler.arun(
                url=source_url,  # Another pass
                config=crawler_config,
            )

            # extract pdf links from markdown result
            pdf_links = extract_pdf_links_from_markdown(markdown_text=result.markdown)

            LOGGER.info(f"✅ HTML Length After Click: {len(result.cleaned_html)}")
            LOGGER.info("\n ======= Preview all the pdf links =======\n")
            LOGGER.info(f"{pdf_links}\n")

            # append to results dict
            results[str(i)] = {
                "url": source_url,
                "links": pdf_links,
                "source_name": source_name
            }

    # Save to JSON file
    output_file = os.path.join(THAIJO_DATA_PATH, "thaijo_pdf_links.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4) # ensure_ascii=False = preserved thai characters
    LOGGER.info(f"✅ Save scraping result to {output_file}")
    LOGGER.info("\n============== End ==============\n")


if __name__ == "__main__":
    # step 1: scrape the website to get overall magazine list & save .md result
    # asyncio.run(crawl_thaijo())

    # step 2: get all the magazine's web urls
    extracted_content = extract_markdown_from_h2(input_filepath=f"{THAIJO_DATA_PATH}/thaijo_markdown.md",
                                                 target_h2_text="วารสารทั้งหมด")
    links = extract_markdown_links_as_json(markdown_text=extracted_content)

    # step 3: extract pdf links through each magazine source
    asyncio.run(cralw_pdf_links(web_urls=links))

    # step 4: get all scraped pdf links
    json_file = os.path.join(THAIJO_DATA_PATH, "thaijo_pdf_links.json")
    all_pdf_links = get_pdf_links_from_json(json_file)
    print(f"all pdf links: {all_pdf_links}")

