import time
import random
import logging
from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup


class ArticleLinkParser:
    """
    Selenium‑based scraper that discovers listing URLs and parses vehicle pages.

    :param headless:    start Chrome headless
    :param delay_range: *(min, max)* random delay to mimic a human
    """

    # ------------------------------------------------------------------ #
    def __init__(self, headless: bool = False, delay_range: tuple[int, int] = (1, 3)):
        self.delay_range = delay_range
        self.driver = None
        self._init_logger()
        self.setup_driver(headless)

    # ------------------------------------------------------------------ #
    #  Logger (instance‑level, name = ``ArticleParser``)
    # ------------------------------------------------------------------ #
    def _init_logger(self):
        self.logger = logging.getLogger("ArticleParser")
        if not self.logger.handlers:                    # configure only once
            sh = logging.StreamHandler()
            sh.setFormatter(logging.Formatter(
                "[ArticleParser]: %(asctime)s  %(levelname)s  %(message)s", "%H:%M:%S"))
            self.logger.addHandler(sh)
            self.logger.setLevel(logging.INFO)

    # ------------------------------------------------------------------ #
    #  Driver setup
    # ------------------------------------------------------------------ #
    def setup_driver(self, headless: bool = False):
        """Create a Chrome driver with lightweight anti‑bot tweaks."""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument(
            "--user-agent="
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")
        self.driver.set_window_size(1366, 768)
        self.logger.info("Chrome driver ready (headless=%s)", headless)

    # ------------------------------------------------------------------ #
    #  Convenience helpers
    # ------------------------------------------------------------------ #
    def human_delay(self, lo: float | None = None, hi: float | None = None):
        lo = self.delay_range[0] if lo is None else lo
        hi = self.delay_range[1] if hi is None else hi
        time.sleep(random.uniform(lo, hi))

    def scroll_page(self, scrolls: int = 3):
        for _ in range(scrolls):
            self.driver.execute_script(
                f"window.scrollBy(0,{random.randint(300,800)});")
            self.human_delay(0.5, 1.5)
        self.driver.execute_script("window.scrollTo(0,0);")
        self.human_delay(1, 2)

    # ------------------------------------------------------------------ #
    #  Link helpers
    # ------------------------------------------------------------------ #
    def get_all_links(self, url: str) -> list[dict]:
        """Return every ``<a>`` element as ``dict(url, text, element)``."""
        self.logger.debug("GET %s", url)
        self.driver.get(url)
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body")))
        self.scroll_page()

        links = []
        for elem in self.driver.find_elements(By.TAG_NAME, "a"):
            if href := elem.get_attribute("href"):
                links.append({"url": urljoin(url, href),
                              "text": elem.text.strip(),
                              "element": elem})
        self.logger.info("Found %d links on page", len(links))
        return links

    def filter_item_links(self, links: list[dict]) -> list[str]:
        """Keep only */item/* links and swap ``#content`` with ``/details``."""
        seen, items = set(), []
        for link in links:
            url = link["url"]
            if "/item/" in url and url.endswith("#content"):
                url = url.replace("#content", "/details")
                if url not in seen:
                    seen.add(url)
                    items.append(url)
        self.logger.debug("Filtered to %d item links", len(items))
        return items

    def get_item_links(self, url: str) -> list[str]:
        try:
            return self.filter_item_links(self.get_all_links(url))
        except Exception as exc:
            self.logger.error("get_item_links failed: %s", exc, exc_info=True)
            return []

    # ------------------------------------------------------------------ #
    #  Vehicle‑page helpers (unchanged logic, logging added)
    # ------------------------------------------------------------------ #
    def get_vehicle_soup(self, vehicle_url: str) -> BeautifulSoup:
        self.human_delay()
        self.driver.get(vehicle_url)
        self.scroll_page()
        return BeautifulSoup(self.driver.page_source, "html.parser")

    def parse_vehicle_details(self, soup: BeautifulSoup):
        header = soup.find(lambda t: t.name == "header"
                                     and "Vehicle extras, add-ons and accessories" in t.get_text())
        items, freetext = [], ""
        if header:
            ul = header.find_next("ul")
            if ul:
                items = [li.get_text(strip=True) for li in ul.find_all("li")]
            div = ul.find_next("div") if ul else None
            if div:
                freetext = div.get_text(strip=True)
        else:
            self.logger.warning("Extras header not found.")
        return items, freetext

    def parse_table_after_header(self, soup: BeautifulSoup, header_text: str):
        header = soup.find(lambda t: t.name == "header" and header_text in t.get_text())
        data = []
        if header:
            table = header.find_next("table")
            if table:
                for row in table.find_all("tr"):
                    data.append([c.get_text(strip=True) for c in row.find_all(["td", "th"])])
            else:
                self.logger.warning("Table missing after '%s'", header_text)
        else:
            self.logger.warning("Header '%s' not found.", header_text)
        return data

    # ------------------------------------------------------------------ #
    #  Pagination – yields batches of unseen links
    # ------------------------------------------------------------------ #
    def scrape_all_links(
        self,
        base_url: str,
        max_pages: int,
        batch_size: int = 10,
        seen_links: set[str] | None = None,
    ):
        """
        Yield batches of *new* listing URLs.

        :param base_url:   search URL without page params
        :param max_pages:  pages to walk
        :param batch_size: emit a list after this many links
        :param seen_links: URLs to skip (already handled)
        """
        seen_links = set() if seen_links is None else seen_links
        batch: list[str] = []

        for page in range(1, max_pages + 1):
            page_url = f"{base_url}&currentPage={page}&pageType=next"
            self.logger.info("Scraping page %d", page)

            for link in self.get_item_links(page_url):
                if link in seen_links:
                    continue
                batch.append(link)
                if len(batch) == batch_size:
                    yield batch
                    batch = []

        if batch:
            yield batch

    # ------------------------------------------------------------------ #
    def close(self):
        """Quit Chrome and log the teardown."""
        if self.driver:
            self.driver.quit()
            self.logger.info("Driver closed")
