"""
Loads the ML model, the user queries, and the 'already mailed' cache.
Runs match() on every Nth vehicle and returns a list of (url, query) hits.
"""

from pathlib import Path
import json
from typing import Iterable, List, Tuple
import random

CACHE_FILE = Path("data/sent.json")
QUERIES_FILE = Path("data/queries.json")

# ------- helpers ---------------------------------------------------------- #

def _load(path: Path, default):
    if path.exists():
        return json.loads(path.read_text())
    return default


def _save(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2))


# ------- public API ------------------------------------------------------- #

class CarMatcher:
    """Stateful matcher that remembers what has been emailed."""

    def __init__(self, model_path: str):
        self.model = self._load_model(model_path)
        self.sent_cache: set[str] = set(_load(CACHE_FILE, []))

    # dummy stub; replace with real model load
    def _load_model(self, path: str):
        import torch
        from transformers import AutoModel

        model = AutoModel.from_pretrained("bert-base-uncased")
        state_dict = torch.load(path, map_location="cpu")
        model.load_state_dict(state_dict)
        model.eval()
        return model

    def _predict(self, query: str, car_json: dict) -> float:
        """Return model score 0–1."""
        return random.random() > 0.7
        # 👉 adapt to your real model’s API
        #features = {**car_json["information"], "details": car_json["details_text"]}
        #return self.model.predict_proba([features, query])[0]

    # ------------------------------------------------------------------ #

    def match(
        self,
        cars: Iterable[dict],
        batch_size: int = 10,
        threshold: float = 0.7,
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
                    continue   # avoid duplicates

                for q in queries:
                    if self._predict(q, car_json) >= threshold:
                        hits.append((url, q))
                        self.sent_cache.add(url)
                        break  # no need to test other queries

            batch.clear()

        if hits:
            _save(CACHE_FILE, sorted(self.sent_cache))
        return hits
