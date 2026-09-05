import json
import shutil
from datetime import datetime
from pathlib import Path

import logging

from resources import default_manifest_path, open_existing_manifest
from models import ContentType, ManifestStatus, ManifestOperation, FileType


class ManifestLogger:
    DEPTH_MAP = {
        FileType.TITLE.value: 0,
        FileType.SEASON.value: 1,
        FileType.EPISODE.value: 2,
        FileType.MOVIE.value: 1
    }

    def __init__(self, content_type: ContentType, original_path: Path, dry_run: bool,
                 manifest_path: Path = None):
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
                self.dump_manifest_to_file()
            self.build_existing_operations()
            logging.debug(f"Resuming manifest with {len(existing_manifest['operations'])} prior operations")
        else:
            self.manifest = self.create_manifest(content_type, original_path)
            if not self.dry_run:
                self.dump_manifest_to_file()
                logging.debug(f"Created manifest at {self.manifest_path}")

    def build_existing_operations(self):
        for op in self.manifest["operations"]:
            if op["status"] == ManifestStatus.COMPLETE.value:
                if op["op_type"] == ManifestOperation.MOVE.value:
                    self.completed_moves[op["from"]] = op["to"]
                    self.completed_moves[op["to"]] = op["to"]

    def dump_manifest_to_file(self):
        if not self.dry_run:
            with open(self.manifest_path, "w", encoding="utf-8") as file:
                json.dump(self.manifest, file, indent=4)

    @staticmethod
    def create_manifest(content_type: ContentType, original_path: Path) -> dict:
        manifest = {
            "timestamp": datetime.now().isoformat(),
            "content_type": content_type.value,
            "original_path": str(original_path),
            "status": ManifestStatus.IN_PROGRESS.value,
            "operations": []
        }
        return manifest

    # --- Operation logging ---

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
        self.dump_manifest_to_file()
        if not self.dry_run:
            shutil.move(from_path, to_path)

        operation["status"] = ManifestStatus.COMPLETE.value
        self.manifest["operations"][-1] = operation
        self.dump_manifest_to_file()

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
        self.dump_manifest_to_file()

        if not self.dry_run:
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
        self.manifest["status"] = ManifestStatus.COMPLETE.value
        self.dump_manifest_to_file()

    # --- Pretty print and helpers ---

    @staticmethod
    def pretty_print(manifest: dict, reverse: bool = False):
        operations = manifest["operations"]
        created_dirs = set()
        for op in operations:
            if op["op_type"] == ManifestOperation.MKDIR.value:
                created_dirs.add(op["path"])

        skip_indices = ManifestLogger.find_skip_indices(operations, created_dirs)
        moves = [op for i, op in enumerate(operations)
                 if i not in skip_indices
                 and op["op_type"] == ManifestOperation.MOVE.value
                 and Path(op["from"]).name != Path(op["to"]).name]

        entries = []
        for op in moves:
            filetype = op["filetype"]
            from_name = Path(op["from"]).name
            to_name = Path(op["to"]).name
            if reverse:
                from_name, to_name = to_name, from_name

            entries.append({"depth": ManifestLogger.DEPTH_MAP[filetype],
                            "filetype": filetype,
                            "from": from_name,
                            "to": to_name})
        ManifestLogger.update_last_entry(entries)
        ManifestLogger.update_parent_continuation(entries)
        ManifestLogger.handle_print(entries)

    @staticmethod
    def find_skip_indices(operations: list, created_dirs: set) -> set:
        skip_indices = set()
        for i, op in enumerate(operations):
            if op["op_type"] == ManifestOperation.MKDIR.value:
                skip_indices.add(i)
            elif op["op_type"] == ManifestOperation.MOVE.value:
                to_parent = str(Path(op["to"]).parent)
                from_parent = str(Path(op["from"]).parent)
                if to_parent in created_dirs and from_parent != to_parent:
                    skip_indices.add(i)
        return skip_indices

    @staticmethod
    def update_last_entry(entries: list):
        for i, entry in enumerate(entries):
            depth = entry["depth"]
            is_last = True
            for future in entries[i + 1:]:
                if future["depth"] == depth:
                    is_last = False
                    break
                if future["depth"] < depth:
                    break
            entry["is_last"] = is_last

    @staticmethod
    def update_parent_continuation(entries: list):
        for i, entry in enumerate(entries):
            if entry["depth"] == 2:
                entry["parent_continues"] = any(e["depth"] == 1 for e in entries[i + 1:])
            else:
                entry["parent_continues"] = False

    @staticmethod
    def handle_print(entries: list):
        for entry in entries:
            label = entry["filetype"].capitalize()
            output = f"{label}: {entry['from']} --> {entry['to']}"

            if entry["depth"] == 0:
                print(output)
            elif entry["depth"] == 1:
                icon = "└" if entry["is_last"] else "├"
                print(f"\t{icon}── {output}")
            elif entry["depth"] == 2:
                icon = "└" if entry["is_last"] else "├"
                vert = "│" if entry["parent_continues"] else " "
                print(f"\t{vert}\t{icon}── {output}")
