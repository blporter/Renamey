import logging
import shutil
from pathlib import Path

from errors import UndoError, InvalidKeys, PathNotDir, DirNotEmpty
from resources import default_manifest_path, open_existing_manifest
from models import ManifestOperation


class Undoer:
    def __init__(self, manifest_path: Path = None):
        path = manifest_path or default_manifest_path()
        self.manifest_path = path.resolve()
        existing_manifest = open_existing_manifest(self.manifest_path)
        if not existing_manifest:
            raise ValueError(f"no valid manifest found at {self.manifest_path}")
        self.manifest = existing_manifest

    @classmethod
    def from_manifest(cls, manifest: dict):
        instance = object.__new__(cls)
        instance.manifest = manifest
        instance.manifest_path = None
        return instance

    def undo_manifest(self):
        if not self.manifest["operations"]:
            raise Exception("no operations to undo")
        for operation in reversed(self.manifest["operations"]):
            self.perform_undo(operation)

        Path(self.manifest_path).unlink(missing_ok=True)
        print("Finished undoing operations, manifest deleted.")

    def undo_last_operation(self):
        if not self.manifest["operations"]:
            raise Exception("no operations to undo")
        operation = self.manifest["operations"].pop()
        logging.debug(f"Undoing last operation: {operation}")
        self.perform_undo(operation)

    def perform_undo(self, operation):
        if operation["op_type"] == ManifestOperation.MOVE.value:
            try:
                self.undo_move(operation)
            except KeyError:
                raise InvalidKeys(operation)

        if operation["op_type"] == ManifestOperation.MKDIR.value:
            try:
                self.undo_mkdir(operation)
            except KeyError:
                raise InvalidKeys(operation)
            except Exception as e:
                raise UndoError(f"failed to undo mkdir operation: {e}")

    @staticmethod
    def undo_move(operation: dict):
        to_path = Path(operation["to"])
        from_path = Path(operation["from"])
        shutil.move(to_path, from_path)
        logging.debug(f"{to_path.name} --> Reverted to --> {from_path.name}")

    @staticmethod
    def undo_mkdir(operation: dict):
        path = Path(operation["path"])
        if not path.is_dir():
            raise PathNotDir(f"{path} is not a directory")
        if any(path.iterdir()):
            raise DirNotEmpty(f"{path} is not empty")
        path.rmdir()
        logging.debug(f"{path.name} --> Reverted directory creation")
