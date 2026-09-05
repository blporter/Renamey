class ManifestAlreadyInProgress(Exception):
    def __init__(self, manifest_path: str):
        self.manifest_path = manifest_path

    def __str__(self):
        return f"manifest already in progress. Resume with `--resume`, use `undo` subcommand to revert it, or delete it from {self.manifest_path}"


class ModelReturnedProse(Exception):
    pass


class UndoError(Exception):
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
