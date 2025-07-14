"""
orchestrator.py – batch‑stream version
"""
from pathlib import Path
from scraper import ArticleLinkParser
from matcher import CarMatcher
from email_util import send_car_email
import logging
import os

# ── CONFIG ────────────────────────────────────────────────────────── #
SEND_FROM   = os.getenv("ALERT_FROM")
SEND_TO     = [addr.strip() for addr in os.getenv("ALERT_TO", "").split(",") if addr]
SMTP_HOST   = os.getenv("SMTP_HOST")
SMTP_PORT   = int(os.getenv("SMTP_PORT", 587))
SMTP_USER   = os.getenv("SMTP_USER")
SMTP_PASSWD = os.getenv("SMTP_PASSWORD")
MODEL_PATH = Path("models/car_matcher.pkl")

BASE_URL    = ("https://autobid.de/en/search-results?"
               "e367=1&sortingType=auctionStartDate-ASCENDING")
MAX_PAGES   = 130
BATCH_SIZE  = 10
THRESHOLD   = 0.7   # 30 % “yes” rate for the coin‑flip matcher
# ------------------------------------------------------------------- #

def parse_vehicle(parser: ArticleLinkParser, url: str) -> dict:
    soup = parser.get_vehicle_soup(url)
    info = parser.parse_table_after_header(soup, "Information")
    details, text = parser.parse_vehicle_details(soup)
    return {
        "url": url,
        "information": {k.rstrip(':'): v for k, v in info},
        "details_list": details,
        "details_text": text,
    }

def run_daily_job():
    # ---------- logger (unchanged) ---------- #
    logger = logging.getLogger("Orchestrator")
    if not logger.handlers:
        sh = logging.StreamHandler()
        sh.setFormatter(logging.Formatter("[Orchestrator]: %(asctime)s  %(levelname)s  %(message)s",
                                          "%H:%M:%S"))
        logger.addHandler(sh)
        logger.setLevel(logging.INFO)

    logger.info("▶ Starting daily scrape & match job")

    parser  = ArticleLinkParser(headless=True, delay_range=(1, 2))
    matcher = CarMatcher(str(MODEL_PATH))
    mailed  = 0

    try:
        for batch_idx, links_chunk in enumerate(
                parser.scrape_all_links(
                    BASE_URL,
                    MAX_PAGES,
                    batch_size=BATCH_SIZE,
                    seen_links=matcher.sent_cache),
                start=1):

            logger.info("• Batch #%02d – %d links", batch_idx, len(links_chunk))

            # ❶ Parse this batch
            cars = [parse_vehicle(parser, url) for url in links_chunk]

            # ❷ Match immediately
            hits = matcher.match(cars,
                                 batch_size=BATCH_SIZE,
                                 threshold=THRESHOLD)

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

        logger.info("✓ Job finished – %s new matches found (mail disabled).",
                    mailed if mailed else "no")
    finally:
        parser.close()
        logger.info("Driver closed")



if __name__ == "__main__":
    run_daily_job()
