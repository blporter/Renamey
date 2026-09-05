import json
import sys
from pathlib import Path

import logging


def resource_dir() -> Path:
    bundle_dir: str | None = getattr(sys, '_MEIPASS', None)
    if bundle_dir is not None:
        return Path(bundle_dir)
    return Path(__file__).resolve().parent.parent


def resource_path(name: str) -> Path:
    return resource_dir() / name


def default_manifest_path() -> Path:
    return Path.home() / ".cache/renamey" / "manifest.json"


def open_existing_manifest(manifest_path: Path = default_manifest_path()) -> dict | None:
    if not manifest_path.exists():
        return None
    with open(manifest_path, "r", encoding="utf-8") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            logging.warning(f"Corrupted manifest file {manifest_path}")
            return None
