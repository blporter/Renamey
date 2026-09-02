import json
from pathlib import Path
from typing import Callable

import pytest

from manifest import ManifestLogger
from models import ContentType, ManifestStatus


class TestManifestMethods:
    # --- Helper methods ---
    @staticmethod
    def create_paths(tmp_path: Path, should_mkdir: bool = True, add_file: str = "") -> Path:
        show_path = tmp_path / "test_show"
        if should_mkdir:
            show_path.mkdir()
        if add_file:
            (show_path / add_file).touch()
        return show_path

    @staticmethod
    def perform_operations(action: Callable, operations: list[tuple[Path] | tuple[Path, Path]]):
        for operation in operations:
            action(*operation)

    # --- Tests for init ---
    def test_init_creates_manifest(self, tmp_path):
        mani = ManifestLogger(ContentType.SHOW, tmp_path / "test_show", False, tmp_path / "test.json")
        assert mani.manifest["content_type"] == ContentType.SHOW.value
        assert mani.manifest["original_path"] == str(tmp_path / "test_show")
        assert mani.manifest["status"] == ManifestStatus.IN_PROGRESS.value
        assert not mani.manifest["operations"]

    def test_init_overwrites_completed_manifest(self, tmp_path):
        test_manifest = {
            "content_type": ContentType.SHOW.value,
            "original_path": str(tmp_path / "test_show"),
            "status": ManifestStatus.COMPLETE.value,
            "operations": []
        }
        with open(tmp_path / "test.json", "w", encoding="utf-8") as file:
            json.dump(test_manifest, file, indent=4)
        mani = ManifestLogger(ContentType.MOVIE, tmp_path / "test_movie", False, tmp_path / "test.json")
        assert mani.manifest["content_type"] == ContentType.MOVIE.value
        assert mani.manifest["status"] == ManifestStatus.IN_PROGRESS.value

    def test_init_skips_on_dry_run(self, tmp_path):
        mani = ManifestLogger(ContentType.MOVIE, tmp_path / "test_movie", True, tmp_path / "test.json")
        with pytest.raises(AttributeError):
            assert mani.manifest is None

    # --- Tests for move ---
    def test_log_move_records_progress(self, tmp_path):
        show_path = self.create_paths(tmp_path)
        mani = ManifestLogger(ContentType.SHOW, show_path, False, tmp_path / "test.json")
        with pytest.raises(FileNotFoundError):
            self.perform_operations(mani.log_move, [(show_path / "test_file1.mkv", show_path / "new_test_file1.mkv")])
        assert mani.manifest["operations"][0]["status"] == ManifestStatus.IN_PROGRESS.value

    def test_log_move_appends_operations(self, tmp_path):
        show_path = self.create_paths(tmp_path)
        operations = [(show_path / "test_file1.mkv", show_path / "new_test_file1.mkv"),
                      (show_path / "test_file2.mkv", show_path / "new_test_file2.mkv"),
                      (show_path / "test_file3.mkv", show_path / "new_test_file3.mkv")]
        for op in operations:
            op[0].touch()
        mani = ManifestLogger(ContentType.SHOW, show_path, False, tmp_path / "test.json")
        self.perform_operations(mani.log_move, operations)
        assert len(mani.manifest["operations"]) == 3

    def test_log_move_marks_operation_complete(self, tmp_path):
        file_names = ("test_file1.mkv", "new_test_file1.mkv")
        show_path = self.create_paths(tmp_path, add_file=file_names[0])
        mani = ManifestLogger(ContentType.SHOW, show_path, False, tmp_path / "test.json")
        self.perform_operations(mani.log_move, [(show_path / file_names[0], show_path / file_names[1])])
        assert mani.manifest["operations"][0]["status"] == ManifestStatus.COMPLETE.value

    def test_log_move_moves_file(self, tmp_path):
        file_names = ("test_file1.mkv", "new_test_file1.mkv")
        show_path = self.create_paths(tmp_path, add_file=file_names[0])
        mani = ManifestLogger(ContentType.SHOW, show_path, False, tmp_path / "test.json")
        self.perform_operations(mani.log_move, [(show_path / file_names[0], show_path / file_names[1])])
        assert not (show_path / file_names[0]).exists()
        assert (show_path / file_names[1]).exists()

    def test_log_move_skips_on_dry_run(self, tmp_path):
        file_names = ("test_file1.mkv", "new_test_file1.mkv")
        mani = ManifestLogger(ContentType.MOVIE, tmp_path / "test_movie", True, tmp_path / "test.json")
        self.perform_operations(mani.log_move, [(tmp_path / file_names[0], tmp_path / file_names[1])])
        with pytest.raises(AttributeError):
            assert mani.manifest["operations"] == []

    # --- Tests for mkdir ---
    def test_log_mkdir_creates_directory(self, tmp_path):
        show_path = self.create_paths(tmp_path)
        mani = ManifestLogger(ContentType.SHOW, show_path, False, tmp_path / "test.json")
        self.perform_operations(mani.log_mkdir, [(show_path / "season_1",)])
        assert (show_path / "season_1").exists()

    def test_log_mkdir_records_in_progress(self, tmp_path, mocker):
        show_path = self.create_paths(tmp_path)
        mani = ManifestLogger(ContentType.SHOW, show_path, False, tmp_path / "test.json")
        mock_mkdir = mocker.patch.object(Path, 'mkdir')
        mock_mkdir.side_effect = OSError("Mocked disk error")
        with pytest.raises(OSError):
            self.perform_operations(mani.log_mkdir, [(show_path / "season_1",)])
        assert mani.manifest["operations"][0]["status"] == ManifestStatus.IN_PROGRESS.value

    def test_log_mkdir_records_failure(self, tmp_path):
        show_path = self.create_paths(tmp_path, False)
        mani = ManifestLogger(ContentType.SHOW, show_path, False, tmp_path / "test.json")
        self.perform_operations(mani.log_mkdir, [(show_path / "season_1",)])
        assert mani.manifest["operations"][0]["status"] == ManifestStatus.FAILED.value

    def test_log_mkdir_appends_operations(self, tmp_path):
        show_path = self.create_paths(tmp_path)
        mani = ManifestLogger(ContentType.SHOW, show_path, False, tmp_path / "test.json")
        operations = [(show_path / "season_1",),
                      (show_path / "season_2",),
                      (show_path / "season_3",)]
        self.perform_operations(mani.log_mkdir, operations)
        assert len(mani.manifest["operations"]) == 3

    def test_log_mkdir_marks_operation_complete(self, tmp_path):
        show_path = self.create_paths(tmp_path)
        mani = ManifestLogger(ContentType.SHOW, show_path, False, tmp_path / "test.json")
        self.perform_operations(mani.log_mkdir, [(show_path / "season_1",)])
        assert mani.manifest["operations"][0]["status"] == ManifestStatus.COMPLETE.value

    def test_log_mkdir_skips_on_dry_run(self, tmp_path):
        mani = ManifestLogger(ContentType.SHOW, tmp_path / "test_show", True, tmp_path / "test.json")
        self.perform_operations(mani.log_mkdir, [(tmp_path / "season_1",)])
        with pytest.raises(AttributeError):
            assert mani.manifest["operations"] == []

    # --- Tests for complete ---
    def test_log_complete_marks_manifest_complete(self, tmp_path):
        mani = ManifestLogger(ContentType.SHOW, tmp_path / "test_show", False, tmp_path / "test.json")
        mani.log_complete()
        assert mani.manifest["status"] == ManifestStatus.COMPLETE.value

    def test_log_complete_skips_on_dry_run(self, tmp_path):
        mani = ManifestLogger(ContentType.SHOW, tmp_path / "test_show", True, tmp_path / "test.json")
        mani.log_complete()
        with pytest.raises(AttributeError):
            assert mani.manifest["status"] == ManifestStatus.COMPLETE.value
