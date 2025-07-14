"""
synonym_batch_generator.py
--------------------------
Generate 1000 natural-language car-query questions with synonym substitution and
score every vehicle from *truncated_vehicles_data.yaml* on a 1-10 scale.

Output:
    /mnt/data/batch_synonym_swap.zip - 10 JSON chunks (100 Qs each, indent=4)

Usage (inside this ChatGPT python_user_visible session):
    python synonym_batch_generator.py
"""

import json, yaml, random, re, zipfile
from pathlib import Path

random.seed(42)

DATA_PATH = "/mnt/data/truncated_vehicles_data.yaml"
OUTPUT_DIR = Path("/mnt/data/batch_synonym_swap")
ZIP_PATH = "/mnt/data/batch_synonym_swap.zip"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

FORBIDDEN_KEYS = {"details_list", "details_text", "information_dict"}

# Synonym pools (≥3 per feature key)
SYNONYMS = {
    "transmission": ["shift", "gearbox", "drive-train"],
    "first registration": ["enrollment", "licensing", "initial log"],
    "power output": ["engine strength", "kW rating", "horse-output"],
    "fuel type": ["propellant", "energy source", "gas kind"],
    "fuel": ["propellant", "energy source", "gas kind"],
    "colour": ["hue", "shade", "paint tone"],
    "color": ["hue", "shade", "paint tone"],
    "mileage": ["odometer reading", "distance travelled", "kilometers shown"],
    "doors": ["entryways", "door count", "access panels"],
    "model": ["variant", "edition", "vehicle line"],
    "category": ["segment", "class", "vehicle group"],
}

STARTERS = ["I am searching for", "Find me", "Are there any", "I would like"]

def load_data(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def numeric_range(value_str):
    nums = re.findall(r"\d+", str(value_str).replace(",", ""))
    if not nums:
        return None
    num = int(nums[0])
    return max(0, int(num * 0.9)), int(num * 1.1)

def build_question(info: dict) -> tuple[str, list[str]]:
    keys = [k for k, v in info.items() if v not in ("", None)]
    if len(keys) < 2:
        raise ValueError("Not enough usable keys")
    kept = random.sample(keys, max(1, len(keys) // 2))

    clauses = []
    for k in kept:
        v = info[k]
        rng = numeric_range(v)
        if rng:
            clauses.append(f"{k} is between {rng[0]} and {rng[1]}")
        else:
            clauses.append(f"{k} equals {v}")

    swappable = [k for k in kept if k.lower() in SYNONYMS]
    if swappable:
        sk = random.choice(swappable)
        clauses = [c.replace(sk, random.choice(SYNONYMS[sk.lower()])) for c in clauses]

    sentence = f"{random.choice(STARTERS)} a car, which " + " and ".join(clauses)
    tokens = sentence.split()
    if len(tokens) > 109:
        sentence = " ".join(tokens[:109])
    return sentence, kept

def relevance(other: dict, ref: dict, used_keys: list[str]) -> int:
    hits = 0
    for k in used_keys:
        ref_val = ref.get(k)
        oth_val = other.get(k)
        if ref_val is None or oth_val is None:
            continue
        rng = numeric_range(ref_val)
        if rng:
            nums = re.findall(r"\d+", str(oth_val).replace(",", ""))
            if nums and rng[0] <= int(nums[0]) <= rng[1]:
                hits += 1
        elif str(ref_val).lower() == str(oth_val).lower():
            hits += 1
    if not used_keys:
        return 1
    if hits == len(used_keys):
        return 10
    return max(1, int(1 + 9 * hits / len(used_keys)))

def main():
    data = load_data(DATA_PATH)

    info_pool = []
    for url, car in data.items():
        info = car.get("information_dict", {})
        if isinstance(info, dict) and len([v for v in info.values() if v not in ("", None)]) >= 2:
            info_pool.append((url, info))

    questions = []
    while len(questions) < 1000:
        url_ref, info_ref = random.choice(info_pool)
        try:
            question, used = build_question(info_ref)
        except ValueError:
            continue
        scores = {
            url: relevance(info, info_ref, used)
            for url, info in info_pool
        }
        questions.append((question, scores))

    # write JSON chunks
    for i in range(10):
        chunk = dict(questions[i * 100:(i + 1) * 100])
        with open(OUTPUT_DIR / f"part_{i+1}.json", "w", encoding="utf-8") as f:
            json.dump(chunk, f, indent=4, ensure_ascii=False)

    # zip
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for i in range(10):
            file_name = f"part_{i+1}.json"
            zf.write(OUTPUT_DIR / file_name, arcname=file_name)

    print(f"Batch created: {ZIP_PATH}")

if __name__ == "__main__":
    main()