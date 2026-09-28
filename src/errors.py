class ManifestAlreadyInProgress(Exception):
    def __init__(self, manifest_path: str):
        self.manifest_path = manifest_path

    def __str__(self):
        return f"manifest already in progress. Resume with `--resume`, use `undo` subcommand to revert it, or delete it from {self.manifest_path}"


class ModelReturnedProse(Exception):
    pass


class UndoError(Exception):
    pass


class NoOperations(UndoError):
    pass


class InvalidKeys(UndoError):
    def __init__(self, operation: dict):
        self.operation = operation

    def __str__(self):
        return f"manifest is missing required fields for operation: {self.operation}"


class PathNotDir(UndoError):
    pass


class DirNotEmpty(UndoError):
    pass

class FileCollisionError(Exception):
    def __init__(self, from_path: str, to_path: str):
        self.from_path = from_path
        self.to_path = to_path

    def __str__(self):
        return (
            f"Cannot move {self.from_path} -> {self.to_path}: file already exists.\n"
            f"Renaming aborted to prevent overwrite. Run `renamey undo` to revert."
        )