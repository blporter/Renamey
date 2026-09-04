import logging
import shutil
from pathlib import Path

from resources import default_manifest_path
from manifest import ManifestLogger
from models import ManifestOperation


class Undoer:
    def __init__(self, manifest_path: Path = default_manifest_path()):
        self.manifest_path = manifest_path.resolve()
        existing_manifest = ManifestLogger.open_existing_manifest(self.manifest_path)
        if not existing_manifest:
            raise ValueError(f"no valid manifest found at {self.manifest_path}")
        self.manifest = existing_manifest

    def undo_manifest(self):
        if not self.manifest["operations"]:
            raise Exception("no operations to undo")
        for operation in reversed(self.manifest["operations"]):
            if operation["op_type"] == ManifestOperation.MOVE.value:
                try:
                    self.undo_move(operation)
                except KeyError:
                    raise KeyError(
                        f"manifest is missing required fields for {ManifestOperation.MOVE.value} operation: {operation}")

            if operation["op_type"] == ManifestOperation.MKDIR.value:
                try:
                    self.undo_mkdir(operation)
                except KeyError:
                    raise KeyError(
                        f"manifest is missing required field for {ManifestOperation.MKDIR.value} operation: {operation}")
                except Exception as e:
                    raise Exception(f"failed to undo mkdir operation: {e}")

        Path(self.manifest_path).unlink(missing_ok=True)
        print("Finished undoing operations, manifest deleted.")

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
            raise Exception(f"{path} is not a directory")
        if any(path.iterdir()):
            raise Exception(f"{path} is not empty")
        path.rmdir()
        logging.debug(f"{path.name} --> Reverted directory creation")
