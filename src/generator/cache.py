import hashlib
import logging
import sqlite3
import numpy as np

from pathlib import Path

from resources import default_embeddings_path


def make_embed_key(model: str, prompt: str) -> str:
    return hashlib.sha256(f"{model}\x00{prompt}".encode("utf-8")).hexdigest()


def to_blob(vector: list[float] | np.ndarray) -> bytes:
    return np.asarray(vector, dtype=np.float32).tobytes()


def from_blob(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)


class EmbedCache:

    def __init__(self, cache_path: Path | None = None):
        self.cache_path = cache_path or default_embeddings_path()
        self.conn: sqlite3.Connection | None = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def open(self):
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(self.cache_path)
            if self.conn is None:
                raise sqlite3.Error("Failed to connect")
            self.conn.execute(
                "CREATE TABLE IF NOT EXISTS embeddings ("
                "key TEXT PRIMARY KEY, model TEXT NOT NULL, vector BLOB NOT NULL"
                ")"
            )
        except (OSError, sqlite3.Error) as e:
            logging.warning(f"Failed to open cache database: {e}")
            self.close()

    def close(self):
        if self.conn is not None:
            try:
                self.conn.commit()
                self.conn.close()
            except sqlite3.Error:
                pass
            self.conn = None

    def get_many(self, keys: list[str]) -> dict[str, np.ndarray]:
        if self.conn is None:
            return {}

        results = {}
        for key in keys:
            cursor = self.conn.execute("SELECT vector FROM embeddings WHERE key=?", (key,))
            hit = cursor.fetchone()
            if hit:
                results[key] = from_blob(hit[0])
        return results

    def put(self, key: str, model: str, vector: list[float] | np.ndarray):
        if self.conn is None:
            return
        try:
            self.conn.execute(
                "INSERT OR REPLACE INTO embeddings (key, model, vector) VALUES (?, ?, ?)",
                (key, model, to_blob(vector))
            )
        except sqlite3.Error as e:
            logging.warning(f"Failed to insert {key} into cache: {e}")
            self.conn.rollback()
            self.close()
