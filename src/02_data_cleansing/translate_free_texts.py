#!/usr/bin/env python3
"""
Translate the free‑text portions of cleaned_vehicles_data.yaml to English
using **Google Translate via `deep_translator`** (no API key required).

Usage:

    python translate_to_english.py \
        --data-file data/cleaned_vehicles_data.yaml \
        --output-file data/translated_vehicles_data.yaml
"""
from __future__ import annotations

import argparse
import logging
import os
from collections import defaultdict
from typing import Mapping, Any

import yaml
from langdetect import detect, LangDetectException
from deep_translator import GoogleTranslator  # pip install deep-translator

# ---------------------------------------------------------------------------
# logging setup
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(sh)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
_MAX_CHARS_PER_REQUEST = 4500  # Google free web translate limit (a bit under 5000)

def _translate(text: str) -> str:
    """Translate *text* to English using Google Translate.

    • Skips empty strings or text already detected as English.
    • Transparently chunks long passages to stay under the request limit.
    • Falls back to the original text on any error and logs the reason.
    """
    if not text or not text.strip():  # nothing to do
        return text

    try:
        try:
            lang = detect(text)
        except LangDetectException:
            lang = "unknown"
        if lang == "en":  # already English
            return text

        translator = GoogleTranslator(source="auto", target="en")

        if len(text) <= _MAX_CHARS_PER_REQUEST:
            return translator.translate(text)

        # --- chunk long passages ---
        chunks: list[str] = [
            text[i : i + _MAX_CHARS_PER_REQUEST]
            for i in range(0, len(text), _MAX_CHARS_PER_REQUEST)
        ]
        translated_chunks: list[str] = []
        for chunk in chunks:
            translated_chunks.append(translator.translate(chunk))
        return "".join(translated_chunks)

    except Exception as exc:  # noqa: BLE001
        logger.error("Google translation failed: %s – returning original text", exc)
        return text

# ---------------------------------------------------------------------------
# main routine
# ---------------------------------------------------------------------------

def translate_yaml(data_file: str, output_file: str) -> None:
    if data_file == output_file:
        raise ValueError("Choose a different output file; don't overwrite the source.")

    with open(data_file, "r", encoding="utf-8") as f:
        data: Mapping[str, Any] = yaml.safe_load(f)

    translated_data: defaultdict[str, Any] = defaultdict(dict)

    remaining = len(data)
    count = 0
    for url, car in data.items():
        translated_entry = dict(car)  # copy so we don't mutate original

        logger.info("Remaining: %d", remaining)
        remaining -= 1
        count += 1

        free_text: str = car.get("details_text", "")
        if not free_text:
            translated_data[url] = translated_entry
            continue

        translated_text = _translate(free_text)
        translated_entry["details_text"] = translated_text

        if translated_text != free_text:
            logger.info("Updated: %s", url)

        translated_data[url] = translated_entry

        if count > 250:
            count = 0
            with open(output_file, "w", encoding="utf-8") as f:
                yaml.dump(translated_data, f, sort_keys=True, allow_unicode=True)

    # write YAML (sorted keys ⇒ stable diffs)
    with open(output_file, "w", encoding="utf-8") as f:
        yaml.dump(translated_data, f, sort_keys=True, allow_unicode=True)

    logger.info("Saved translated file → %s", output_file)

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data'))

    default_input = os.path.join(base_dir, "cleaned_vehicles_data.yaml")
    default_output = os.path.join(base_dir, "translated_vehicles_data.yaml")

    ap = argparse.ArgumentParser(description="Translate free-text fields to English (Google Translate)")
    ap.add_argument("--data-file", type=str, default=default_input)
    ap.add_argument("--output-file", type=str, default=default_output)
    args = ap.parse_args()

    translate_yaml(**vars(args))
