#!/usr/bin/env python3
"""
Translate the free‑text portions of cleaned_vehicles_data.yaml to English.

Usage:

    python translate_to_english.py \
        --data-file data/cleaned_vehicles_data.yaml \
        --output-file data/translated_vehicles_data.yaml

Environment variables:
    OPENAI_API_KEY  – Your OpenAI API key.
    OPENAI_MODEL    – (optional) Chat model to use; default: ``gpt-4o-mini``.
"""
from __future__ import annotations

import argparse
import logging
import os
from collections import defaultdict
from typing import Dict, Any

import yaml
from langdetect import detect, LangDetectException  # type: ignore
from openai import OpenAI

# ---------------------------------------------------------------------------
# logging setup
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(sh)

# ---------------------------------------------------------------------------
# OpenAI client (re‑usable across calls)
# ---------------------------------------------------------------------------
OPENAI_API_KEY = "XXXX"
if not OPENAI_API_KEY:
    logger.warning(
        "OPENAI_API_KEY not set – _translate will simply echo the source text."
    )

_client: OpenAI | None = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


# ---------------------------------------------------------------------------
# Translation utility
# ---------------------------------------------------------------------------

def _translate(text: str, *, target_lang: str = "English") -> str:  # noqa: D401
    """Translate *text* to *English* via the OpenAI Chat Completion API.

    If the language is already English, the original text is returned unchanged.
    The function automatically chunks very long inputs so that each call remains
    comfortably inside the model's context window (≈16 K tokens for **gpt‑4o-mini**).

    Parameters
    ----------
    text
        The text to translate.
    target_lang
        Kept for future flexibility. Currently fixed to English.
    """
    # Fast exit for empty strings
    if not text.strip():
        return text

    # If no API key is configured, fall back to returning the source text
    if _client is None:
        return text

    # Detect source language – catch failures quietly
    try:
        src_lang = detect(text[:256])  # analyse only initial 256 chars for speed
    except LangDetectException:
        src_lang = "unknown"

    if src_lang.lower().startswith("en"):
        return text  # already English → nothing to do

    def _translate_chunk(chunk: str) -> str:
        """Translate a single chunk (helper)."""
        response = _client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a professional translator. Translate the user's text to technical English "
                        "while preserving meaning, units, and simple markdown "
                        "formatting. Return *only* the translation – no extra explanations. For context, the text is about cars"
                    ),
                },
                {"role": "user", "content": chunk},
            ],
        )
        return response.choices[0].message.content.strip()

    # --- simple character‑based chunking -----------------------------------
    MAX_CHARS = 8_000  # ≈4 K tokens – stay well within model limits

    if len(text) <= MAX_CHARS:
        try:
            return _translate_chunk(text)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("OpenAI translation failed: %s – returning original text", exc)
            return text

    # Split large texts into paragraphs, keeping ›MAX_CHARS‹ safety margin
    out_chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for para in text.split("\n\n"):
        if current_len + len(para) > MAX_CHARS:
            try:
                out_chunks.append(_translate_chunk("\n\n".join(current)))
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("OpenAI translation failed: %s – embedding un‑translated chunk", exc)
                out_chunks.append("\n\n".join(current))
            current = [para]
            current_len = len(para)
        else:
            current.append(para)
            current_len += len(para)

    if current:
        try:
            out_chunks.append(_translate_chunk("\n\n".join(current)))
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("OpenAI translation failed: %s – embedding un‑translated chunk", exc)
            out_chunks.append("\n\n".join(current))

    return "\n\n".join(out_chunks)


# ---------------------------------------------------------------------------
# Main routine
# ---------------------------------------------------------------------------

def translate_yaml(data_file: str, output_file: str) -> None:  # noqa: D401
    """Translate the *details_text* field of each entry in *data_file* to English."""
    if data_file == output_file:
        raise ValueError("Choose a different output file; don't overwrite the source.")

    with open(data_file, "r", encoding="utf-8") as f:
        data: Dict[str, Dict[str, Any]] = yaml.safe_load(f)

    translated_data: Dict[str, Dict[str, Any]] = defaultdict(dict)

    remaining = len(data)
    for url, car in data.items():
        logger.info("Remaining: %s", remaining)
        remaining -= 1

        translated_entry = dict(car)
        free_text = car.get("details_text", "")

        if free_text:
            translated_text = _translate(free_text)
            translated_entry["details_text"] = translated_text
            if translated_text != free_text:
                logger.info("Updated: %s", url)

        translated_data[url] = translated_entry

    # --- write YAML with sorted keys for stable diffs ----------------------
    with open(output_file, "w", encoding="utf-8") as f:
        yaml.dump(translated_data, f, sort_keys=True, allow_unicode=True)

    logger.info("Saved translated file → %s", output_file)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    repo_root = os.path.dirname(__file__)
    default_input = os.path.join(repo_root, "data", "cleaned_vehicles_data.yaml")
    default_output = os.path.join(repo_root, "data", "translated_vehicles_data.yaml")

    ap = argparse.ArgumentParser(description="Translate free‑text fields to English")
    ap.add_argument("--data-file", type=str, default=default_input)
    ap.add_argument("--output-file", type=str, default=default_output)
    opts = ap.parse_args()

    translate_yaml(opts.data_file, opts.output_file)
