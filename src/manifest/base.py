import logging

from datetime import datetime
from pathlib import Path

from resources import default_manifest_path, open_existing_manifest
from models import ContentType, ManifestStatus, ManifestOperation, FileType
from .logger import LoggingHelper
from .print import pretty_print


def create_manifest(content_type: ContentType, original_path: Path) -> dict:
    manifest = {
        "timestamp": datetime.now().isoformat(),
        "content_type": content_type.value,
        "original_path": str(original_path),
        "status": ManifestStatus.IN_PROGRESS.value,
        "operations": []
    }
    return manifest


class Manifest:

    def __init__(self, content_type: ContentType, original_path: Path, dry_run: bool,
                 manifest_path: Path | None = None):
        path = manifest_path or default_manifest_path()
        self.manifest_path = path.resolve()
        if not self.manifest_path.parent.exists():
            self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.dry_run = dry_run
        self.completed_moves = {}

        existing_manifest = open_existing_manifest(self.manifest_path)
        if existing_manifest and existing_manifest["status"] == ManifestStatus.IN_PROGRESS.value:
            self.manifest = existing_manifest
            if not self.dry_run:
                LoggingHelper.dump_manifest_to_file(self.manifest_path, self.manifest, self.dry_run)
            self.build_existing_operations()
            logging.debug(f"Resuming manifest with {len(existing_manifest['operations'])} prior operations")
        else:
            self.manifest = create_manifest(content_type, original_path)
            if not self.dry_run:
                LoggingHelper.dump_manifest_to_file(self.manifest_path, self.manifest, self.dry_run)
                logging.debug(f"Created manifest at {self.manifest_path}")
        self.logger = LoggingHelper(self.manifest, self.manifest_path, dry_run)

    def build_existing_operations(self):
        for op in self.manifest["operations"]:
            if op["status"] == ManifestStatus.COMPLETE.value:
                if op["op_type"] == ManifestOperation.MOVE.value:
                    self.completed_moves[op["from"]] = op["to"]
                    self.completed_moves[op["to"]] = op["to"]

    @staticmethod
    def print(manifest: dict, reverse: bool = False):
        pretty_print(manifest, reverse)
