import json
import os
import re
import argparse
import logging
from typing import Iterable

import yaml


# ---------------------------------------------------------------------------
# logging setup
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(
    logging.Formatter("%(levelname)s: %(message)s")
)
logger.addHandler(stream_handler)


# ---------------------------------------------------------------------------
# helper to strip duplicate phrases
# ---------------------------------------------------------------------------
def _dedupe_details_text(details_text: str,
                         details_list: Iterable[str],
                         info_values: Iterable[str]) -> str:
    phrases = {p.lower().strip() for p in details_list if p.strip()}
    phrases.update(str(v).lower().strip() for v in info_values if v)

    for phrase in sorted(phrases, key=len, reverse=True):
        if not phrase:
            continue
        pattern = re.compile(rf"\b{re.escape(phrase)}\b[.,;:]?", re.IGNORECASE)
        details_text = pattern.sub("", details_text)

    # Remove extra whitespace and punctuation
    details_text = re.sub(r"\s{2,}", " ", details_text)
    details_text = re.sub(r"[;,]{2,}", ";", details_text)
    details_text = re.sub(r"^[\s;,.]+|[\s;,.]+$", "", details_text)

    return details_text.strip()


# ---------------------------------------------------------------------------
# main cleaner
# ---------------------------------------------------------------------------
def cleanse_data(data_file: str, output_file: str):
    if data_file == output_file:
        raise ValueError("Choose a different output file; don't overwrite the source.")
    if not data_file.endswith(".json"):
        raise ValueError("cleanse_data only accepts .json files.")

    with open(data_file, "r", encoding="utf-8") as read_file:
        original_data = json.load(read_file)
    if not original_data:
        raise ValueError("The provided file is empty—nothing to clean.")

    cleaned_data = {}

    for url, car_dict in original_data.items():
        details_list = car_dict.get("details_list", [])
        info_dict = car_dict.get("information_dict", {})
        details_text = car_dict.get("details_text", "")

        # skip incomplete rows
        if not (all(details_list) and all(info_dict.values()) and details_text):
            logger.warning("Skipped incomplete entry for %s", url)
            continue

        cleaned_text = _dedupe_details_text(
            details_text,
            details_list,
            info_dict.values()
        )

        if cleaned_text != details_text:
            logger.info("Modified details_text for %s", url)

        cleaned_entry = dict(car_dict)
        cleaned_entry["details_text"] = cleaned_text
        cleaned_data[url] = cleaned_entry

    # Save sorted YAML for readability
    with open(output_file, "w", encoding="utf-8") as write_file:
        yaml.dump(cleaned_data, write_file, sort_keys=True, allow_unicode=True)

    logger.info(f"Saved the cleaned data as: {output_file}")

    return cleaned_data


# ---------------------------------------------------------------------------
# CLI wrapper
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    default_data_file = os.path.join(
        os.path.dirname(__file__),
        "data",
        "vehicles_data.json"
    )
    default_output_file = os.path.join(
        os.path.dirname(__file__),
        "data",
        "cleaned_vehicles_data.yaml"
    )

    parser = argparse.ArgumentParser()
    parser.add_argument("--data-file", type=str, default=default_data_file)
    parser.add_argument("--output-file", type=str, default=default_output_file)
    args = parser.parse_args()

    cleanse_data(**vars(args))
