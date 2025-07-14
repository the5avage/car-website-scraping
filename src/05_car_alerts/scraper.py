"""
Wrap the existing Selenium scraper so it *yields* one vehicle at a time.
That lets the matcher run in parallel or in small batches.
"""

from collections.abc import Iterator
from article_parser import ArticleLinkParser  # your original code


def vehicle_generator(base_url: str, max_pages: int) -> Iterator[dict]:
    """Yield dicts shaped like the JSON you already save."""
    parser = ArticleLinkParser(headless=True, delay_range=(1, 2))

    try:
        links = parser.scrape_all_links(base_url, max_pages)

        for url in links:
            soup = parser.get_vehicle_soup(url)
            info = parser.parse_table_after_header(soup, "Information")
            details, text = parser.parse_vehicle_details(soup)

            yield {
                "url": url,
                "information": {k.rstrip(':'): v for k, v in info},
                "details_list": details,
                "details_text": text,
            }
    finally:
        parser.close()
