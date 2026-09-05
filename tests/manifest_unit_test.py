import json
from pathlib import Path
from typing import Callable

import pytest

from manifest import ManifestLogger
from models import ContentType, ManifestStatus, ManifestOperation, FileType


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
    def perform_operations(action: Callable, operations: list[tuple]):
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

    def test_init_records_timestamp(self, tmp_path):
        mani = ManifestLogger(ContentType.SHOW, tmp_path / "test_show", False, tmp_path / "test.json")
        assert "timestamp" in mani.manifest

    def test_init_writes_manifest_to_disk(self, tmp_path):
        ManifestLogger(ContentType.SHOW, tmp_path / "test_show", False, tmp_path / "test.json")
        assert (tmp_path / "test.json").exists()
        with open(tmp_path / "test.json", encoding="utf-8") as file:
            data = json.load(file)
        assert data["status"] == ManifestStatus.IN_PROGRESS.value

    def test_init_resumes_in_progress_manifest(self, tmp_path):
        existing = {
            "timestamp": "2020-01-01T00:00:00",
            "content_type": ContentType.SHOW.value,
            "original_path": str(tmp_path / "test_show"),
            "status": ManifestStatus.IN_PROGRESS.value,
            "operations": [{
                "op_type": ManifestOperation.MOVE.value,
                "from": str(tmp_path / "from_a.mkv"),
                "to": str(tmp_path / "to_b.mkv"),
                "filetype": FileType.EPISODE.value,
                "status": ManifestStatus.COMPLETE.value,
            }],
        }
        with open(tmp_path / "test.json", "w", encoding="utf-8") as file:
            json.dump(existing, file, indent=4)
        mani = ManifestLogger(ContentType.MOVIE, tmp_path / "ignored", False, tmp_path / "test.json")
        assert mani.manifest["content_type"] == ContentType.SHOW.value
        assert len(mani.manifest["operations"]) == 1
        assert mani.completed_moves[str(tmp_path / "from_a.mkv")] == str(tmp_path / "to_b.mkv")

    def test_init_skips_disk_write_on_dry_run(self, tmp_path):
        mani = ManifestLogger(ContentType.MOVIE, tmp_path / "test_movie", True, tmp_path / "test.json")
        assert mani.manifest["status"] == ManifestStatus.IN_PROGRESS.value
        assert not (tmp_path / "test.json").exists()

    # --- Tests for move ---

    def test_log_move_records_progress(self, tmp_path):
        show_path = self.create_paths(tmp_path)
        mani = ManifestLogger(ContentType.SHOW, show_path, False, tmp_path / "test.json")
        with pytest.raises(FileNotFoundError):
            self.perform_operations(mani.log_move, [(show_path / "test_file1.mkv", show_path / "new_test_file1.mkv",
                                                     FileType.EPISODE)])
        assert mani.manifest["operations"][0]["status"] == ManifestStatus.IN_PROGRESS.value

    def test_log_move_appends_operations(self, tmp_path):
        show_path = self.create_paths(tmp_path)
        operations = [(show_path / "test_file1.mkv", show_path / "new_test_file1.mkv", FileType.EPISODE),
                      (show_path / "test_file2.mkv", show_path / "new_test_file2.mkv", FileType.EPISODE),
                      (show_path / "test_file3.mkv", show_path / "new_test_file3.mkv", FileType.EPISODE)]
        for op in operations:
            op[0].touch()
        mani = ManifestLogger(ContentType.SHOW, show_path, False, tmp_path / "test.json")
        self.perform_operations(mani.log_move, operations)
        assert len(mani.manifest["operations"]) == 3

    def test_log_move_marks_operation_complete(self, tmp_path):
        file_names = ("test_file1.mkv", "new_test_file1.mkv")
        show_path = self.create_paths(tmp_path, add_file=file_names[0])
        mani = ManifestLogger(ContentType.SHOW, show_path, False, tmp_path / "test.json")
        self.perform_operations(mani.log_move,
                                [(show_path / file_names[0], show_path / file_names[1], FileType.EPISODE)])
        assert mani.manifest["operations"][0]["status"] == ManifestStatus.COMPLETE.value

    def test_log_move_moves_file(self, tmp_path):
        file_names = ("test_file1.mkv", "new_test_file1.mkv")
        show_path = self.create_paths(tmp_path, add_file=file_names[0])
        mani = ManifestLogger(ContentType.SHOW, show_path, False, tmp_path / "test.json")
        self.perform_operations(mani.log_move,
                                [(show_path / file_names[0], show_path / file_names[1], FileType.EPISODE)])
        assert not (show_path / file_names[0]).exists()
        assert (show_path / file_names[1]).exists()

    def test_log_move_records_filetype(self, tmp_path):
        file_names = ("test_file1.mkv", "new_test_file1.mkv")
        show_path = self.create_paths(tmp_path, add_file=file_names[0])
        mani = ManifestLogger(ContentType.SHOW, show_path, False, tmp_path / "test.json")
        self.perform_operations(mani.log_move,
                                [(show_path / file_names[0], show_path / file_names[1], FileType.EPISODE)])
        assert mani.manifest["operations"][0]["filetype"] == FileType.EPISODE.value

    def test_log_move_skips_duplicate_operation(self, tmp_path):
        file_names = ("test_file1.mkv", "new_test_file1.mkv")
        show_path = self.create_paths(tmp_path, add_file=file_names[0])
        mani = ManifestLogger(ContentType.SHOW, show_path, False, tmp_path / "test.json")
        mani.log_move(show_path / file_names[0], show_path / file_names[1], FileType.EPISODE)
        mani.log_move(show_path / file_names[0], show_path / file_names[1], FileType.EPISODE)
        assert len(mani.manifest["operations"]) == 1

    def test_log_move_skips_on_dry_run(self, tmp_path):
        file_names = ("test_file1.mkv", "new_test_file1.mkv")
        show_path = self.create_paths(tmp_path, add_file=file_names[0])
        mani = ManifestLogger(ContentType.SHOW, show_path, True, tmp_path / "test.json")
        self.perform_operations(mani.log_move,
                                [(show_path / file_names[0], show_path / file_names[1], FileType.EPISODE)])
        assert (show_path / file_names[0]).exists()
        assert not (show_path / file_names[1]).exists()
        assert not (tmp_path / "test.json").exists()

    # --- Tests for mkdir ---

    def test_log_mkdir_creates_directory(self, tmp_path):
        show_path = self.create_paths(tmp_path)
        mani = ManifestLogger(ContentType.SHOW, show_path, False, tmp_path / "test.json")
        self.perform_operations(mani.log_mkdir, [(show_path / "season_1", FileType.SEASON)])
        assert (show_path / "season_1").exists()

    def test_log_mkdir_records_in_progress(self, tmp_path, mocker):
        show_path = self.create_paths(tmp_path)
        mani = ManifestLogger(ContentType.SHOW, show_path, False, tmp_path / "test.json")
        mock_mkdir = mocker.patch.object(Path, 'mkdir')
        mock_mkdir.side_effect = OSError("Mocked disk error")
        with pytest.raises(OSError):
            self.perform_operations(mani.log_mkdir, [(show_path / "season_1", FileType.SEASON)])
        assert mani.manifest["operations"][0]["status"] == ManifestStatus.IN_PROGRESS.value

    def test_log_mkdir_records_failure(self, tmp_path):
        show_path = self.create_paths(tmp_path, False)
        mani = ManifestLogger(ContentType.SHOW, show_path, False, tmp_path / "test.json")
        self.perform_operations(mani.log_mkdir, [(show_path / "season_1", FileType.SEASON)])
        assert mani.manifest["operations"][0]["status"] == ManifestStatus.FAILED.value

    def test_log_mkdir_appends_operations(self, tmp_path):
        show_path = self.create_paths(tmp_path)
        mani = ManifestLogger(ContentType.SHOW, show_path, False, tmp_path / "test.json")
        operations = [(show_path / "season_1", FileType.SEASON),
                      (show_path / "season_2", FileType.SEASON),
                      (show_path / "season_3", FileType.SEASON)]
        self.perform_operations(mani.log_mkdir, operations)
        assert len(mani.manifest["operations"]) == 3

    def test_log_mkdir_marks_operation_complete(self, tmp_path):
        show_path = self.create_paths(tmp_path)
        mani = ManifestLogger(ContentType.SHOW, show_path, False, tmp_path / "test.json")
        self.perform_operations(mani.log_mkdir, [(show_path / "season_1", FileType.SEASON)])
        assert mani.manifest["operations"][0]["status"] == ManifestStatus.COMPLETE.value

    def test_log_mkdir_skips_on_dry_run(self, tmp_path):
        show_path = self.create_paths(tmp_path)
        mani = ManifestLogger(ContentType.SHOW, show_path, True, tmp_path / "test.json")
        self.perform_operations(mani.log_mkdir, [(show_path / "season_1", FileType.SEASON)])
        assert not (show_path / "season_1").exists()
        assert not (tmp_path / "test.json").exists()

    # --- Tests for complete ---

    def test_log_complete_marks_manifest_complete(self, tmp_path):
        mani = ManifestLogger(ContentType.SHOW, tmp_path / "test_show", False, tmp_path / "test.json")
        mani.log_complete()
        assert mani.manifest["status"] == ManifestStatus.COMPLETE.value

    def test_log_complete_skips_disk_write_on_dry_run(self, tmp_path):
        mani = ManifestLogger(ContentType.SHOW, tmp_path / "test_show", True, tmp_path / "test.json")
        mani.log_complete()
        assert not (tmp_path / "test.json").exists()


def move_op(frm, to, filetype):
    return {"op_type": ManifestOperation.MOVE.value, "from": frm, "to": to,
            "filetype": filetype.value, "status": "complete"}


def mkdir_op(path):
    return {"op_type": ManifestOperation.MKDIR.value, "path": path,
            "filetype": FileType.SEASON.value, "status": "complete"}


class TestManifestPrettyPrint:

    def test_find_skip_indices_skips_mkdir_and_structural_moves(self):
        operations = [
            mkdir_op("/show/Season 01"),
            move_op("/show/ep.mkv", "/show/Season 01/ep.mkv", FileType.EPISODE),
            move_op("/show/a.mkv", "/show/a2.mkv", FileType.EPISODE),
        ]
        created_dirs = {"/show/Season 01"}
        assert ManifestLogger.find_skip_indices(operations, created_dirs) == {0, 1}

    def test_find_skip_indices_keeps_in_place_rename(self):
        operations = [
            move_op("/show/Season 01/old.mkv", "/show/Season 01/new.mkv", FileType.EPISODE),
        ]
        created_dirs = {"/show/Season 01"}
        assert ManifestLogger.find_skip_indices(operations, created_dirs) == set()

    def test_update_last_entry_marks_final_at_each_depth(self):
        entries = [{"depth": 1}, {"depth": 2}, {"depth": 1}]
        ManifestLogger.update_last_entry(entries)
        assert [entry["is_last"] for entry in entries] == [False, True, True]

    def test_update_last_entry_single_entry_is_last(self):
        entries = [{"depth": 0}]
        ManifestLogger.update_last_entry(entries)
        assert entries[0]["is_last"] is True

    def test_update_parent_continuation_flags_depth_two(self):
        entries = [{"depth": 2}, {"depth": 1}, {"depth": 2}]
        ManifestLogger.update_parent_continuation(entries)
        assert [entry["parent_continues"] for entry in entries] == [True, False, False]

    def test_update_parent_continuation_false_when_no_following_season(self):
        entries = [{"depth": 1}, {"depth": 2}]
        ManifestLogger.update_parent_continuation(entries)
        assert [entry["parent_continues"] for entry in entries] == [False, False]

    # --- Handle pretty print ---

    def test_handle_print_title_depth_zero(self, capsys):
        ManifestLogger.handle_print([
            {"depth": 0, "filetype": FileType.TITLE.value, "from": "a", "to": "b",
             "is_last": True, "parent_continues": False},
        ])
        assert capsys.readouterr().out.strip() == "Title: a --> b"

    def test_handle_print_indents_by_depth(self, capsys):
        entries = [
            {"depth": 1, "filetype": FileType.SEASON.value, "from": "s1", "to": "s2",
             "is_last": False, "parent_continues": False},
            {"depth": 2, "filetype": FileType.EPISODE.value, "from": "e1", "to": "e2",
             "is_last": True, "parent_continues": True},
        ]
        ManifestLogger.handle_print(entries)
        lines = capsys.readouterr().out.splitlines()
        assert lines[0] == "\t├── Season: s1 --> s2"
        assert lines[1] == "\t│\t└── Episode: e1 --> e2"

    def test_pretty_print_filters_and_renders(self, capsys):
        manifest = {"operations": [
            move_op("/root/Bad Title", "/root/Frieren", FileType.TITLE),
            mkdir_op("/root/Frieren/Season 01"),
            move_op("/root/Frieren/Season 01/messy.mkv",
                    "/root/Frieren/Season 01/Frieren E01.mkv", FileType.EPISODE),
            move_op("/root/Frieren/skip.mkv",
                    "/root/Frieren/Season 01/skip.mkv", FileType.EPISODE),
        ]}
        ManifestLogger.pretty_print(manifest)
        out = capsys.readouterr().out
        assert "Title: Bad Title --> Frieren" in out
        assert "Episode: messy.mkv --> Frieren E01.mkv" in out
        assert "skip.mkv" not in out

    def test_pretty_print_reverse_swaps_direction(self, capsys):
        manifest = {"operations": [
            move_op("/root/Bad Title", "/root/Frieren", FileType.TITLE),
        ]}
        ManifestLogger.pretty_print(manifest, reverse=True)
        assert "Title: Frieren --> Bad Title" in capsys.readouterr().out
