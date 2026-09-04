import sys
from pathlib import Path


def resource_dir() -> Path:
    bundle_dir: str | None = getattr(sys, '_MEIPASS', None)
    if bundle_dir is not None:
        return Path(bundle_dir)
    return Path(__file__).resolve().parent.parent


def resource_path(name: str) -> Path:
    return resource_dir() / name

def default_manifest_path() -> Path:
    return Path.home() / ".cache/renamey" / "manifest.json"
