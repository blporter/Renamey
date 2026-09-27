import json
import logging
import shutil

from pathlib import Path

from models import ManifestOperation, ManifestStatus, FileType


class LoggingHelper:

    def __init__(self, manifest: dict, manifest_path: Path, dry_run: bool):
        self.manifest = manifest
        self.manifest_path = manifest_path
        self.dry_run = dry_run

    @staticmethod
    def dump_manifest_to_file(manifest_path: Path, manifest: dict, dry_run: bool):
        if not dry_run:
            with open(manifest_path, "w", encoding="utf-8") as file:
                json.dump(manifest, file, indent=4)

    def log_move(self, from_path: Path, to_path: Path, filetype: FileType):
        operation = {
            "op_type": ManifestOperation.MOVE.value,
            "from": str(from_path),
            "to": str(to_path),
            "filetype": filetype.value,
            "status": ManifestStatus.COMPLETE.value
        }
        if operation in self.manifest["operations"]:
            logging.debug(f"Skipping move operation for {from_path} --> {to_path}, already in manifest")
            return
        operation["status"] = ManifestStatus.IN_PROGRESS.value
        self.manifest["operations"].append(operation)
        self.dump_manifest_to_file(self.manifest_path, self.manifest, self.dry_run)
        if not self.dry_run:
            shutil.move(from_path, to_path)

        operation["status"] = ManifestStatus.COMPLETE.value
        self.manifest["operations"][-1] = operation
        self.dump_manifest_to_file(self.manifest_path, self.manifest, self.dry_run)

    def log_mkdir(self, path: Path, filetype: FileType):
        operation = {
            "op_type": ManifestOperation.MKDIR.value,
            "path": str(path),
            "filetype": filetype.value,
            "status": ManifestStatus.COMPLETE.value
        }
        if operation in self.manifest["operations"]:
            logging.debug(f"Skipping mkdir operation for {path}, already in manifest")
            return
        operation["status"] = ManifestStatus.IN_PROGRESS.value
        self.manifest["operations"].append(operation)
        self.dump_manifest_to_file(self.manifest_path, self.manifest, self.dry_run)

        if not self.dry_run:
            try:
                path.mkdir(parents=False, exist_ok=True)
            except FileNotFoundError as e:
                logging.warning(f"Skipping season directory, problem with structure: {e}")
                operation["status"] = ManifestStatus.FAILED.value
                self.manifest["operations"][-1] = operation
                self.dump_manifest_to_file(self.manifest_path, self.manifest, self.dry_run)
                return

        operation["status"] = ManifestStatus.COMPLETE.value
        self.manifest["operations"][-1] = operation
        self.dump_manifest_to_file(self.manifest_path, self.manifest, self.dry_run)

    def log_complete(self):
        self.manifest["status"] = ManifestStatus.COMPLETE.value
        self.dump_manifest_to_file(self.manifest_path, self.manifest, self.dry_run)
