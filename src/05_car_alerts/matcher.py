"""
Loads the ML model, the user queries, and the 'already mailed' cache.
Runs match() on every Nth vehicle and returns a list of (url, query) hits.
"""

# standard library
import json
import random
from pathlib import Path
from typing import Iterable, List, Tuple
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

CACHE_FILE = Path("data/sent.json")
QUERIES_FILE = Path("data/queries.json")

# ------- helpers ---------------------------------------------------------- #


def _load(path: Path, default):
    if path.exists():
        return json.loads(path.read_text())
    return default


def _save(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2))


class CarMatcher:
    """Stateful matcher that remembers what has been emailed, using a local file."""

    def __init__(self, model_path: str):
        self.model, self.tokenizer = self._load_model(model_path)
        self.sent_cache: set[str] = set(_load(CACHE_FILE, []))
        self.max_length = 512  # Same as used in training
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

    def _load_model(self, path: str):
        """Load the fine-tuned DeBERTa model and tokenizer."""
        print(f"Loading model from: {path}")

        # Load tokenizer and model from the saved directory
        tokenizer = AutoTokenizer.from_pretrained(path)
        model = AutoModelForSequenceClassification.from_pretrained(path)
        model.eval()

        print("Model loaded successfully")
        return model, tokenizer

    def _create_vehicle_description(self, car_json: dict) -> str:
        """Create a comprehensive vehicle description from the car data.
        This should match the format used during training."""
        description_parts = []

        # Add information dictionary details
        if 'information_dict' in car_json:
            info_dict = car_json['information_dict']
            for key, value in info_dict.items():
                description_parts.append(f"{key}: {value}")

        # Add details list
        if 'details_list' in car_json:
            details = " | ".join(car_json['details_list'])
            description_parts.append(details)

        # Add details text if available
        if 'details_text' in car_json:
            description_parts.append(car_json['details_text'])

        # Fallback: if the structure is different, try to extract key info
        if not description_parts:
            # Handle alternative structure
            if 'information' in car_json:
                for key, value in car_json['information'].items():
                    description_parts.append(f"{key}: {value}")

            if 'details' in car_json:
                description_parts.append(car_json['details'])

        return " | ".join(description_parts)

    def predict(self, query: str, car_json: dict) -> float:
        """Return model score 0–1 for how well the query matches the car."""

        # Create vehicle description in the same format as training
        vehicle_text = self._create_vehicle_description(car_json)

        # Tokenize the query-vehicle pair (cross-encoder format)
        encoding = self.tokenizer(
            query,
            vehicle_text,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )

        # Move to device
        encoding = {k: v.to(self.device) for k, v in encoding.items()}

        # Make prediction
        with torch.no_grad():
            outputs = self.model(**encoding)
            # Get probability of positive class (index 1) - match probability
            predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
            match_probability = predictions[0][1].item()

        return match_probability

    def match(
        self,
        cars: Iterable[dict],
        batch_size: int = 10,
        threshold: float = 0.5,
    ) -> List[Tuple[str, str]]:
        """
        Iterate over cars, score every batch of *batch_size* vehicles.
        Returns the first ‑time hits; updates sent.json on the fly.
        """
        queries: list[str] = _load(QUERIES_FILE, [])
        batch: list[dict] = []
        hits: list[Tuple[str, str]] = []

        for car in cars:
            batch.append(car)

            if len(batch) < batch_size:
                continue

            for car_json in batch:
                url = car_json["url"]
                if url in self.sent_cache:
                    continue  # avoid duplicates

                for q in queries:
                    if self._predict(q, car_json) >= threshold:
                        hits.append((url, q))
                        self.sent_cache.add(url)
                        break  # no need to test other queries

            batch.clear()

        if hits:
            _save(CACHE_FILE, sorted(self.sent_cache))
        return hits
