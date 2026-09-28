import csv
import logging
import re
import ollama

from pathlib import Path
from typing import Any

import numpy as np
from tqdm import tqdm

from models import FileType
from .cache import EmbedCache, make_embed_key

SEASON_COMPILE = re.compile(r"^Season \d+$", re.IGNORECASE)
EPISODE_COMPILE = re.compile(r"\bE\d{2,}\b", re.IGNORECASE)


def classify_reference(clean_name: str) -> FileType:
    name = clean_name.strip()
    if EPISODE_COMPILE.search(name):
        return FileType.EPISODE
    if SEASON_COMPILE.match(name):
        return FileType.SEASON
    return FileType.TITLE


def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    denominator = np.linalg.norm(v1) * np.linalg.norm(v2)
    if np.isclose(denominator, 0.0):
        return 0.0
    return float(np.dot(v1, v2) / denominator)


class EmbedHelper:
    EMBED_MODEL = "nomic-embed-text"

    def __init__(self, csv_path: Path, cache_path: Path | None = None):
        self.cache = EmbedCache(cache_path)
        self.examples = self.load_reference(csv_path)

    def load_reference(self, csv_path: Path) -> list[dict[str, Any]]:
        logging.info(f"Loading from reference file {csv_path}")

        with open(csv_path, mode="r", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file, delimiter="\t")
            prepared = []
            for row in reader:
                if not row["messy_name"].strip():
                    continue
                prompt = f"search_document: {row['messy_name'].lower()}"
                key = make_embed_key(self.EMBED_MODEL, prompt)
                prepared.append((row, prompt, key))

        with self.cache:
            keys = [item[2] for item in prepared]
            vectors = self.cache.get_many(keys)

            missing = [item for item in prepared if item[2] not in vectors]
            iterator = missing
            if missing:
                tqdm.write(
                    f"First-time setup: generating embeddings for {len(missing)} reference entries. "
                    "This only happens once and will be cached for next time."
                )
                iterator = tqdm(
                    missing,
                    desc="Preparing references",
                    unit="ref",
                    bar_format="{l_bar}{bar:60}{r_bar}",
                    ascii="░█",
                )

            for row, prompt, key in iterator:
                response = ollama.embeddings(model=self.EMBED_MODEL, prompt=prompt)
                vector = response["embedding"]
                vectors[key] = vector
                self.cache.put(key, self.EMBED_MODEL, vector)

        return [{
            "messy": row["messy_name"],
            "clean": row["clean_name"],
            "type": classify_reference(row["clean_name"]).value,
            "vector": vectors[key],
        } for row, prompt, key in prepared]

    def get_useful_references(self, filename: str, filetype: FileType) -> list[dict[str, Any]]:
        target_res = ollama.embeddings(model=self.EMBED_MODEL, prompt=f"search_query: {filename.lower()}")
        target_vector = np.array(target_res["embedding"])

        candidates = [e for e in self.examples if e["type"] == filetype.value] or self.examples

        scores = []
        for example in candidates:
            similarity = cosine_similarity(target_vector, example["vector"])
            scores.append((similarity, example))

        scores.sort(key=lambda x: x[0], reverse=True)
        limit = 2 if filetype == FileType.SEASON else 4

        got_references = {
            score[0]: {
                "messy": score[1]["messy"],
                "clean": score[1]["clean"],
                "type": score[1]["type"],
            }
            for score in scores[:limit]
        }
        logging.debug(f"For filename {filename}, got references {got_references}")
        return [item[1] for item in scores[:limit]]
