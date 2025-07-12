import os
from typing import List, Dict
from pathlib import Path
import re
from pathlib import Path
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode, BrowserConfig
from utils.logger import setup_logging


ROOT_PATH = os.getcwd()
CRAWL_PATH = os.path.join(ROOT_PATH, 'crawl')
DATA_PATH = os.path.join(ROOT_PATH, 'data')
THAIJO_DATA_PATH = os.path.join(DATA_PATH, 'thaijo')
LOGGER = setup_logging(log_file=os.path.join(THAIJO_DATA_PATH, "thaijo_scrape.log"))


URL = "https://www.tci-thaijo.org/"


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


if __name__ == "__main__":
    asyncio.run(crawl_thaijo())

    extracted_content = extract_markdown_from_h2(input_filepath=f"{THAIJO_DATA_PATH}/thaijo_markdown.md",
                                                 target_h2_text="วารสารทั้งหมด")
    links = extract_markdown_links_as_json(markdown_text=extracted_content)
    