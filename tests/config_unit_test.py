import json
from argparse import Namespace

import pytest

import resources
from resources import (
    DEFAULT_TITLE_MODEL,
    DEFAULT_EPISODE_MODEL,
    open_existing_config,
    write_config,
)
from parser import FileParser
from models import RenameArguments, ConfigArguments, ContentType


def write_config_file(path, config):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(config, file, indent=4)
    return config


@pytest.fixture
def config_path(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    monkeypatch.setattr(resources, "default_config_path", lambda: path)
    return path


class TestConfigArgs:
    def test_returns_defaults_when_file_missing(self, tmp_path):
        title_model, episode_model = open_existing_config(tmp_path / "missing.json")
        assert title_model == DEFAULT_TITLE_MODEL
        assert episode_model == DEFAULT_EPISODE_MODEL

    def test_returns_defaults_on_empty_config(self, tmp_path):
        path = tmp_path / "config.json"
        write_config_file(path, {})
        title_model, episode_model = open_existing_config(path)
        assert title_model == DEFAULT_TITLE_MODEL
        assert episode_model == DEFAULT_EPISODE_MODEL

    def test_returns_defaults_on_corrupted_config(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text("{not valid json", encoding="utf-8")
        title_model, episode_model = open_existing_config(path)
        assert title_model == DEFAULT_TITLE_MODEL
        assert episode_model == DEFAULT_EPISODE_MODEL

    def test_partial_config_fills_missing_with_defaults(self, tmp_path, subtests):
        cases = [
            ({"title_model": "custom-title"}, "custom-title", DEFAULT_EPISODE_MODEL),
            ({"episode_model": "custom-episode"}, DEFAULT_TITLE_MODEL, "custom-episode"),
        ]
        for config, expected_title, expected_episode in cases:
            with subtests.test(config=config):
                path = tmp_path / "config.json"
                write_config_file(path, config)
                title_model, episode_model = open_existing_config(path)
                assert title_model == expected_title
                assert episode_model == expected_episode

    def test_returns_stored_values_when_present(self, tmp_path):
        path = tmp_path / "config.json"
        write_config_file(path, {"title_model": "custom-title", "episode_model": "custom-episode"})
        title_model, episode_model = open_existing_config(path)
        assert title_model == "custom-title"
        assert episode_model == "custom-episode"

    def test_logs_warning_on_corrupted_config(self, tmp_path, caplog):
        path = tmp_path / "config.json"
        path.write_text("{not valid json", encoding="utf-8")
        with caplog.at_level("WARNING"):
            open_existing_config(path)
        assert any("Corrupted config file" in record.message for record in caplog.records)

    def test_writes_config_to_disk(self, tmp_path):
        path = tmp_path / "config.json"
        write_config({"title_model": "custom-title", "episode_model": "custom-episode"}, path)
        with open(path, "r", encoding="utf-8") as file:
            assert json.load(file) == {"title_model": "custom-title", "episode_model": "custom-episode"}

    def test_creates_missing_parent_directories(self, tmp_path):
        path = tmp_path / "nested" / "dir" / "config.json"
        write_config({"title_model": "t", "episode_model": "e"}, path)
        assert path.exists()

    def test_round_trips_with_open_existing_config(self, tmp_path):
        path = tmp_path / "config.json"
        write_config({"title_model": "round-title", "episode_model": "round-episode"}, path)
        assert open_existing_config(path) == ("round-title", "round-episode")

    def test_defaults_written_when_no_flags_and_no_config(self, config_path):
        result = FileParser.handle_config_args(Namespace(title_model=None, episode_model=None))
        assert isinstance(result, ConfigArguments)
        assert result.has_updated_config is True
        assert open_existing_config(config_path) == (DEFAULT_TITLE_MODEL, DEFAULT_EPISODE_MODEL)

    def test_flags_are_persisted(self, config_path):
        FileParser.handle_config_args(Namespace(title_model="new-title", episode_model="new-episode"))
        assert open_existing_config(config_path) == ("new-title", "new-episode")

    def test_partial_flag_preserves_existing_value(self, config_path):
        write_config({"title_model": "old-title", "episode_model": "old-episode"}, config_path)
        FileParser.handle_config_args(Namespace(title_model="updated-title", episode_model=None))
        assert open_existing_config(config_path) == ("updated-title", "old-episode")
