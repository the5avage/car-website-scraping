"""
orchestrator.py – batch‑stream version
"""

# standard library
import logging
import os
from pathlib import Path

# third party libraries
import yaml

# project imports
from email_util import send_car_email
from matcher import CarMatcher
from scraper import ArticleLinkParser

# ── CONFIG ────────────────────────────────────────────────────────── #
CONFIG = yaml.safe_load(
    (Path(__file__).parent / "config" / "orchestrator.yaml").read_text()
)
# SMTP
SEND_FROM = CONFIG["smtp"]["from"]
SEND_TO = CONFIG["smtp"]["to"]
SMTP_HOST = CONFIG["smtp"]["host"]
SMTP_PORT = CONFIG["smtp"]["port"]
SMTP_USER = CONFIG["smtp"]["user"]
SMTP_PASSWD = CONFIG["smtp"]["password"]

# Scraper
BASE_URL = CONFIG["scraper"]["base_url"]
MAX_PAGES = CONFIG["scraper"]["max_pages"]
BATCH_SIZE = CONFIG["scraper"]["batch_size"]

# Matcher
THRESHOLD = CONFIG["matcher"]["threshold"]
MODEL_PATH = CONFIG["matcher"]["model_path"]
# ------------------------------------------------------------------- #

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def _save_batch_to_yaml(batch: list[dict], logger):
    """
    Append *batch* to the current YAML file, skipping URLs that
    already exist; start a new file after 3 000 entries.
    """
    # discover latest file
    files = sorted(DATA_DIR.glob("vehicles_data_*.yaml"))
    if files:
        current = files[-1]
        with current.open("r", encoding="utf-8") as fh:
            try:
                existing = yaml.safe_load(fh) or {}
            except yaml.YAMLError:
                existing = {}
    else:
        current = DATA_DIR / "vehicles_data_1.yaml"
        existing = {}

    # quick look‑up of URLs already saved
    seen_urls = set(existing.keys())

    added = 0
    for car in batch:
        url = car["url"]
        if url in seen_urls:
            continue
        existing[url] = car
        seen_urls.add(url)
        added += 1

        # rollover if > 3000
        if len(existing) >= 3000:
            with current.open("w", encoding="utf-8") as fh:
                yaml.safe_dump(existing, fh, allow_unicode=True)
            logger.info("Saved 3 000 rows → %s", current.name)
            # start fresh
            idx = int(current.stem.split("_")[-1]) + 1
            current = DATA_DIR / f"vehicles_data_{idx}.yaml"
            existing = {}
            seen_urls.clear()

    # write back (tail file may be < 3000)
    if added:
        with current.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(existing, fh, allow_unicode=True)
        logger.info("Appended %d new rows → %s", added, current.name)


def parse_vehicle(parser: ArticleLinkParser, url: str) -> dict:
    soup = parser.get_vehicle_soup(url)
    info = parser.parse_table_after_header(soup, "Information")
    details, text = parser.parse_vehicle_details(soup)
    return {
        "url": url,
        "information": {k.rstrip(":"): v for k, v in info},
        "details_list": details,
        "details_text": text,
    }


def run_daily_job():
    # ---------- logger (unchanged) ---------- #
    logger = logging.getLogger("Orchestrator")
    if not logger.handlers:
        sh = logging.StreamHandler()
        sh.setFormatter(
            logging.Formatter(
                "[Orchestrator]: %(asctime)s  %(levelname)s  %(message)s", "%H:%M:%S"
            )
        )
        logger.addHandler(sh)
        logger.setLevel(logging.INFO)

    logger.info("▶ Starting daily scrape & match job")

    parser = ArticleLinkParser(
        headless=CONFIG["scraper"]["headless"],
        delay_range=tuple(CONFIG["scraper"]["delay"]),
    )
    matcher = CarMatcher(str(MODEL_PATH))
    mailed = 0

    try:
        for batch_idx, links_chunk in enumerate(
            parser.scrape_all_links(
                BASE_URL,
                MAX_PAGES,
                batch_size=BATCH_SIZE,
                seen_links=matcher.sent_cache,
            ),
            start=1,
        ):

            logger.info("• Batch #%02d – %d links", batch_idx, len(links_chunk))

            # ❶ Parse this batch
            cars = [parse_vehicle(parser, url) for url in links_chunk]

            _save_batch_to_yaml(cars, logger)

            # ❷ Match immediately
            hits = matcher.match(cars, batch_size=BATCH_SIZE, threshold=THRESHOLD)

            if hits:
                mailed += len(hits)
                logger.info("  ↪ %d hits – would send e‑mail", len(hits))

                # -------------------------------------------------------
                # send_car_email(
                #     send_from=SEND_FROM,
                #     send_to=SEND_TO,
                #     recipiant_name="User",
                #     found_cars=hits,
                #     smtp_host=SMTP_HOST,
                #     smtp_port=SMTP_PORT,
                #     smtp_user=SMTP_USER,
                #     smtp_password=SMTP_PASSWD,
                # )
                # -------------------------------------------------------

        logger.info(
            "✓ Job finished – %s new matches found (mail disabled).",
            mailed if mailed else "no",
        )
    finally:
        parser.close()
        logger.info("Driver closed")


if __name__ == "__main__":
    run_daily_job()
