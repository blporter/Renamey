import json
import sys
from pathlib import Path

import logging

DEFAULT_TITLE_MODEL = "gemma4:e4b-mlx"
DEFAULT_EPISODE_MODEL = "llama3.1:8b"


def resource_dir() -> Path:
    bundle_dir: str | None = getattr(sys, '_MEIPASS', None)
    if bundle_dir is not None:
        return Path(bundle_dir)
    return Path(__file__).resolve().parent.parent


def resource_path(name: str) -> Path:
    return resource_dir() / name


def default_manifest_path() -> Path:
    return Path.home() / ".cache/renamey" / "manifest.json"


def default_embeddings_path() -> Path:
    return Path.home() / ".cache/renamey" / "embeddings.sqlite"


def default_config_path() -> Path:
    return Path.home() / ".cache/renamey" / "config.json"


def open_existing_manifest(manifest_path: Path = None) -> dict | None:
    path = (manifest_path or default_manifest_path()).resolve()
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            logging.warning(f"Corrupted manifest file {path}")
            return None


def open_existing_config(config_path: Path = None) -> tuple[str, str]:
    path = (config_path or default_config_path()).resolve()
    config = {}
    if path.exists():
        with open(path, "r", encoding="utf-8") as file:
            try:
                config = json.load(file)
            except json.JSONDecodeError:
                logging.warning(f"Corrupted config file {path}")
    title_model = config.get("title_model", DEFAULT_TITLE_MODEL)
    episode_model = config.get("episode_model", DEFAULT_EPISODE_MODEL)
    return title_model, episode_model


def write_config(config: dict, config_path: Path = None):
    path = (config_path or default_config_path()).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(config, file, indent=4)
