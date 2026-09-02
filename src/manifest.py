import json
import shutil
from datetime import datetime
from pathlib import Path

import logging

from models import ContentType, ManifestStatus, ManifestOperation


class ManifestLogger:
    def __init__(self, content_type: ContentType, original_path: Path, dry_run: bool,
                 manifest_path: Path = Path.home() / ".renamey_manifest.json"):
        self.manifest_path = manifest_path.resolve()
        self.dry_run = dry_run
        if self.dry_run:
            return
        existing_manifest = self.open_existing_manifest()
        if existing_manifest and existing_manifest["status"] == ManifestStatus.IN_PROGRESS.value:
            logging.info("A manifest is already in progress")
            # TODO: Handle resume of an interrupt
            raise Exception("A manifest is already in progress")
        self.manifest = self.create_manifest(content_type, original_path)
        self.dump_manifest_to_file()
        logging.debug(f"Created manifest at {self.manifest_path}")

    def open_existing_manifest(self) -> dict | None:
        if not self.manifest_path.exists():
            return None
        with open(self.manifest_path, "r", encoding="utf-8") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                logging.warning(f"Corrupted manifest file {self.manifest_path}, overwriting with empty manifest")
                return None

    def dump_manifest_to_file(self):
        with open(self.manifest_path, "w", encoding="utf-8") as file:
            json.dump(self.manifest, file, indent=4)

    def create_manifest(self, content_type: ContentType, original_path: Path) -> dict:
        if self.dry_run:
            return {}
        manifest = {
            "timestamp": datetime.now().isoformat(),
            "content_type": content_type.value,
            "original_path": str(original_path),
            "status": ManifestStatus.IN_PROGRESS.value,
            "operations": []
        }
        return manifest

    def log_move(self, from_path: Path, to_path: Path):
        if self.dry_run:
            return
        operation = {
            "type": ManifestOperation.MOVE.value,
            "from": str(from_path),
            "to": str(to_path),
            "status": ManifestStatus.IN_PROGRESS.value
        }
        self.manifest["operations"].append(operation)
        self.dump_manifest_to_file()

        shutil.move(from_path, to_path)

        operation["status"] = ManifestStatus.COMPLETE.value
        self.manifest["operations"][-1] = operation
        self.dump_manifest_to_file()

    def log_mkdir(self, path: Path):
        if self.dry_run:
            return
        operation = {
            "type": ManifestOperation.MKDIR.value,
            "path": str(path),
            "status": ManifestStatus.IN_PROGRESS.value
        }
        self.manifest["operations"].append(operation)
        self.dump_manifest_to_file()

        try:
            path.mkdir(parents=False, exist_ok=True)
        except FileNotFoundError as e:
            logging.warning(f"Skipping season directory, problem with structure: {e}")
            operation["status"] = ManifestStatus.FAILED.value
            self.manifest["operations"][-1] = operation
            self.dump_manifest_to_file()
            return

        operation["status"] = ManifestStatus.COMPLETE.value
        self.manifest["operations"][-1] = operation
        self.dump_manifest_to_file()

    def log_complete(self):
        if self.dry_run:
            return
        self.manifest["status"] = ManifestStatus.COMPLETE.value
        self.dump_manifest_to_file()
