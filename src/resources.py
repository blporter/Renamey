import json
import logging
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_TITLE_MODEL = "gemma4:e4b-mlx"
DEFAULT_EPISODE_MODEL = "llama3.1:8b"
DEFAULT_REFERENCE_URL = "https://raw.githubusercontent.com/blporter/Renamey/main/src/assets/naming_reference.csv"


def is_bundled() -> bool:
    return getattr(sys, "_MEIPASS", None) is not None


def resource_dir() -> Path:
    bundle_dir: str | None = getattr(sys, "_MEIPASS", None)
    if bundle_dir is not None:
        return Path(bundle_dir) / "assets"
    return Path(__file__).resolve().parent / "assets"


def resource_path(name: str) -> Path:
    return resource_dir() / name


def default_manifest_path() -> Path:
    return Path.home() / ".cache/renamey" / "manifest.json"


def default_embeddings_path() -> Path:
    return Path.home() / ".cache/renamey" / "embeddings.sqlite"


def default_config_path() -> Path:
    return Path.home() / ".cache/renamey" / "config.json"


def default_reference_path() -> Path:
    return Path.home() / ".cache/renamey" / "naming_reference.csv"


def default_reference_etag_path() -> Path:
    return Path.home() / ".cache/renamey" / "naming_reference.etag"


def fetch_remote_reference(url: str = DEFAULT_REFERENCE_URL, destination: Path | None = None,
                           etag_path: Path | None = None, timeout: float = 3.0) -> Path | None:
    dest = (destination or default_reference_path()).resolve()
    etag_file = (etag_path or default_reference_etag_path()).resolve()

    headers = {}
    if etag_file.exists() and dest.exists():
        try:
            etag_val = etag_file.read_text(encoding="utf-8").strip()
            if etag_val:
                headers["If-None-Match"] = etag_val
        except OSError as e:
            logging.debug(f"Failed to read etag file: {e}")

    req = urllib.request.Request(url, headers=headers)
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        etag_file.parent.mkdir(parents=True, exist_ok=True)

        with urllib.request.urlopen(req, timeout=timeout) as response:
            content = response.read()
            dest.write_bytes(content)
            new_etag = response.headers.get("ETag")
            if new_etag:
                etag_file.write_text(new_etag.strip(), encoding="utf-8")
                logging.debug(f"Updated etag file with new value: {new_etag}")
            return dest

    except urllib.error.HTTPError as e:
        if e.code == 304 and dest.exists():
            logging.debug("Remote reference not modified (304). Using cached copy.")
            return dest
        logging.warning(f"HTTP error fetching remote reference: {e}")
        return None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        logging.warning(f"Failed to fetch remote reference from {url}: {e}")
        return None


def get_reference_path(url: str = DEFAULT_REFERENCE_URL, cache_path: Path | None = None, etag_path: Path | None = None,
                       force_local: bool = False, timeout: float = 3.0) -> Path:
    if not is_bundled() or force_local:
        return resource_path("naming_reference.csv")

    cached_dest = (cache_path or default_reference_path()).resolve()
    fetched = fetch_remote_reference(url, cached_dest, etag_path, timeout)
    if fetched is not None and fetched.exists():
        return fetched

    if cached_dest.exists():
        logging.info("Using previously cached reference after remote fetch failed")
        return cached_dest

    logging.info("Falling back to bundled reference file")
    return resource_path("naming_reference.csv")


def open_existing_manifest(manifest_path: Path | None = None) -> dict | None:
    path = (manifest_path or default_manifest_path()).resolve()
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            logging.warning(f"Corrupted manifest file {path}")
            return None


def open_existing_config(config_path: Path | None = None) -> tuple[str, str]:
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


def write_config(config: dict, config_path: Path | None = None):
    path = (config_path or default_config_path()).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(config, file, indent=4)
