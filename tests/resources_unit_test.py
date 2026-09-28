import sys
import urllib.error
import urllib.request
from email.message import Message
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

import resources
from models import RenameArguments, ContentType
from main import Renamey

MEIPASS = "_MEIPASS"


class TestResources:
    @pytest.fixture
    def dest(self, tmp_path):
        return tmp_path / "cache" / "naming_reference.csv"

    @pytest.fixture
    def etag_file(self, tmp_path):
        return tmp_path / "cache" / "naming_reference.etag"

    def test_is_bundled_false_when_meipass_not_set(self, monkeypatch):
        monkeypatch.delattr(sys, MEIPASS, raising=False)
        assert resources.is_bundled() is False

    def test_is_bundled_true_when_meipass_set(self, monkeypatch, tmp_path):
        monkeypatch.setattr(sys, MEIPASS, str(tmp_path), raising=False)
        assert resources.is_bundled() is True

    def test_get_reference_path_returns_local_when_not_bundled(self, monkeypatch):
        monkeypatch.delattr(sys, MEIPASS, raising=False)
        path = resources.get_reference_path()
        assert path == resources.resource_path("naming_reference.csv")
        assert path.exists()

    def test_get_reference_path_returns_local_when_force_local_true(self, monkeypatch, tmp_path):
        monkeypatch.setattr(sys, MEIPASS, str(tmp_path), raising=False)
        path = resources.get_reference_path(force_local=True)
        assert path == resources.resource_path("naming_reference.csv")

    def test_fetch_remote_reference_success_200(self, dest, etag_file, monkeypatch):
        mock_response = MagicMock()
        mock_response.read.return_value = b"messy_name\tclean_name\nShow.S01E01\tShow E01\n"
        mock_response.headers.get.return_value = '"etag-12345"'
        mock_response.__enter__.return_value = mock_response

        monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout: mock_response)

        result = resources.fetch_remote_reference(
            url="https://example.com/ref.csv",
            destination=dest,
            etag_path=etag_file,
            timeout=1.0,
        )

        assert result == dest
        assert dest.exists()
        assert "Show.S01E01" in dest.read_text(encoding="utf-8")
        assert etag_file.exists()
        assert etag_file.read_text(encoding="utf-8") == '"etag-12345"'

    def test_fetch_remote_reference_304_not_modified(self, dest, etag_file, monkeypatch):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("existing cached content", encoding="utf-8")
        etag_file.write_text('"etag-12345"', encoding="utf-8")

        sent_headers = {}

        def mock_urlopen(req, *args, **kwargs):
            sent_headers.update(req.headers)
            raise urllib.error.HTTPError(
                url="https://example.com/ref.csv",
                code=304,
                msg="Not Modified",
                hdrs=Message(),
                fp=BytesIO(),
            )

        monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

        result = resources.fetch_remote_reference(
            url="https://example.com/ref.csv",
            destination=dest,
            etag_path=etag_file,
            timeout=1.0,
        )

        assert result == dest
        assert dest.read_text(encoding="utf-8") == "existing cached content"
        assert sent_headers.get("If-none-match") == '"etag-12345"'

    def test_fetch_remote_reference_network_error_returns_none(self, dest, etag_file, monkeypatch):
        def mock_urlopen(*args, **kwargs):
            raise urllib.error.URLError("Connection refused")

        monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

        result = resources.fetch_remote_reference(
            url="https://example.com/ref.csv",
            destination=dest,
            etag_path=etag_file,
            timeout=1.0,
        )

        assert result is None

    def test_get_reference_path_bundled_success(self, tmp_path, dest, etag_file, monkeypatch):
        monkeypatch.setattr(sys, MEIPASS, str(tmp_path), raising=False)

        mock_response = MagicMock()
        mock_response.read.return_value = b"messy_name\tclean_name\nShow.S01E01\tShow E01\n"
        mock_response.headers.get.return_value = '"etag-12345"'
        mock_response.__enter__.return_value = mock_response

        monkeypatch.setattr(urllib.request, "urlopen", lambda req, *args, **kwargs: mock_response)

        path = resources.get_reference_path(
            cache_path=dest,
            etag_path=etag_file,
        )
        assert path == dest
        assert path.exists()

    def test_get_reference_path_bundled_fallback_to_cached_when_network_fails(self, tmp_path, dest, monkeypatch):
        monkeypatch.setattr(sys, MEIPASS, str(tmp_path), raising=False)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("previously cached content", encoding="utf-8")

        def mock_urlopen(*args, **kwargs):
            raise urllib.error.URLError("Network down")

        monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

        path = resources.get_reference_path(
            cache_path=dest,
        )
        assert path == dest
        assert path.read_text(encoding="utf-8") == "previously cached content"

    def test_get_reference_path_bundled_fallback_to_bundled_when_no_cache_and_network_fails(self, tmp_path,
                                                                                            dest,
                                                                                            monkeypatch):
        bundled_asset_dir = tmp_path / "assets"
        bundled_asset_dir.mkdir(parents=True, exist_ok=True)
        (bundled_asset_dir / "naming_reference.csv").write_text("bundled content", encoding="utf-8")

        monkeypatch.setattr(sys, MEIPASS, str(tmp_path), raising=False)

        def mock_urlopen(*args, **kwargs):
            raise urllib.error.URLError("Network down")

        monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

        path = resources.get_reference_path(
            cache_path=dest,
        )
        assert path == resources.resource_path("naming_reference.csv")
        assert path.exists()
        assert path.read_text(encoding="utf-8") == "bundled content"

    def test_renamey_initialization_passes_resolved_reference(self, tmp_path, monkeypatch):
        test_csv = tmp_path / "custom_reference.csv"
        test_csv.write_text("messy_name\tclean_name\n", encoding="utf-8")
        monkeypatch.setattr("main.get_reference_path", lambda: test_csv)

        folder = tmp_path / "media_folder"
        folder.mkdir()
        (folder / "file1.mkv").touch()

        args = RenameArguments(
            content_type=ContentType.SHOW,
            filepath=folder,
            title_model="test-title-model",
            episode_model="test-episode-model",
            dry_run=True,
            resume=False,
        )

        with patch("main.Generator") as mock_gen_class:
            renamey = Renamey(args, ignore_set=set())
            mock_gen_class.assert_called_once_with(
                test_csv, "test-title-model", "test-episode-model"
            )
            assert renamey.filepath == folder
