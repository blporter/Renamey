import json
import pytest

from undoer import Undoer
from errors import UndoError, InvalidKeys, PathNotDir, DirNotEmpty, NoOperations
from models import ManifestOperation


def move_op(from_path, to_path):
    return {"op_type": ManifestOperation.MOVE.value, "from": str(from_path), "to": str(to_path),
            "status": "complete"}


def mkdir_op(path):
    return {"op_type": ManifestOperation.MKDIR.value, "path": str(path), "status": "complete"}


def write_manifest(path, operations):
    manifest = {"content_type": "show", "original_path": str(path.parent),
                "status": "complete", "operations": operations}
    with open(path, "w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=4)
    return manifest


class TestUndoerMethods:

    def test_init_raises_when_manifest_missing(self, tmp_path):
        with pytest.raises(ValueError):
            Undoer(tmp_path / "missing.json")

    def test_init_raises_on_corrupted_manifest(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{not valid json", encoding="utf-8")
        with pytest.raises(ValueError):
            Undoer(path)

    def test_init_loads_existing_manifest(self, tmp_path):
        path = tmp_path / "manifest.json"
        manifest = write_manifest(path, [mkdir_op(tmp_path / "season_1")])
        undoer = Undoer(path)
        assert undoer.manifest == manifest
        assert undoer.manifest_path == path.resolve()

    def test_from_manifest_sets_attributes(self):
        manifest = {"operations": []}
        undoer = Undoer.from_manifest(manifest)
        assert undoer.manifest is manifest
        assert undoer.manifest_path is None

    def test_undo_move_reverts_file(self, tmp_path):
        from_path = tmp_path / "from.mkv"
        to_path = tmp_path / "to.mkv"
        to_path.touch()
        undoer = Undoer.from_manifest({"operations": [move_op(from_path, to_path)]})
        undoer.undo_last_operation()
        assert from_path.exists()
        assert not to_path.exists()
        assert undoer.manifest["operations"] == []

    def test_perform_undo_move_missing_keys_raises_invalid_keys(self):
        bad = {"op_type": ManifestOperation.MOVE.value, "from": "/x/a.mkv", "status": "complete"}
        undoer = Undoer.from_manifest({"operations": [bad]})
        with pytest.raises(InvalidKeys):
            undoer.undo_last_operation()

    def test_undo_mkdir_removes_empty_directory(self, tmp_path):
        target = tmp_path / "season_1"
        target.mkdir()
        undoer = Undoer.from_manifest({"operations": [mkdir_op(target)]})
        undoer.undo_last_operation()
        assert not target.exists()

    def test_undo_mkdir_raises_on_non_dir(self, tmp_path):
        with pytest.raises(PathNotDir):
            Undoer.undo_mkdir({"path": str(tmp_path / "does_not_exist")})

    def test_undo_mkdir_raises_on_non_empty_dir(self, tmp_path):
        target = tmp_path / "season_1"
        target.mkdir()
        (target / "ep.mkv").touch()
        with pytest.raises(DirNotEmpty):
            Undoer.undo_mkdir({"path": str(target)})

    def test_perform_undo_propagates_path_not_dir(self, tmp_path):
        undoer = Undoer.from_manifest({"operations": [mkdir_op(tmp_path / "missing")]})
        with pytest.raises(PathNotDir):
            undoer.undo_last_operation()

    def test_perform_undo_propagates_dir_not_empty(self, tmp_path):
        target = tmp_path / "season_1"
        target.mkdir()
        (target / "ep.mkv").touch()
        undoer = Undoer.from_manifest({"operations": [mkdir_op(target)]})
        with pytest.raises(DirNotEmpty):
            undoer.undo_last_operation()

    def test_undo_manifest_reverts_all_and_deletes_file(self, tmp_path):
        show = tmp_path / "show"
        show.mkdir()
        season = show / "Season 01"
        season.mkdir()
        moved = season / "ep.mkv"
        moved.touch()
        original = show / "ep.mkv"

        path = tmp_path / "manifest.json"
        write_manifest(path, [mkdir_op(season), move_op(original, moved)])
        undoer = Undoer(path)
        undoer.undo_manifest()

        assert original.exists()
        assert not season.exists()
        assert not path.exists()

    def test_undo_manifest_raises_without_operations(self, tmp_path):
        path = tmp_path / "manifest.json"
        write_manifest(path, [])
        undoer = Undoer(path)
        with pytest.raises(NoOperations):
            undoer.undo_manifest()

    def test_undo_last_operation_raises_without_operations(self):
        undoer = Undoer.from_manifest({"operations": []})
        with pytest.raises(NoOperations):
            undoer.undo_last_operation()
