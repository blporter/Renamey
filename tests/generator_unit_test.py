import math
import sqlite3
import pytest
import numpy as np

from pathlib import Path
from unittest.mock import patch

from generator import Generator
from generator.embed import classify_reference, cosine_similarity
from generator.prompt import PromptHelper
from generator.cache import make_embed_key, from_blob, to_blob, EmbedCache
from models import FileType, Prompts
from errors import ModelReturnedProse

MOCK_CSV = Path(__file__).resolve().parent / "mock_reference.csv"


@pytest.fixture(scope="module")
def generator(tmp_path_factory):
    cache_path = tmp_path_factory.mktemp("cache") / "embeddings.sqlite"
    with patch("generator.embed.ollama") as mock_ollama:
        mock_ollama.embeddings.return_value = {"embedding": [1.0, 0.0]}
        return Generator(MOCK_CSV, "", "", cache_path=cache_path)


@pytest.fixture(autouse=True)
def reset_title_name(generator):
    generator.title_name = ""


class TestGeneratorMethods:
    def test_classify_returns_expected_filetypes(self):
        assert FileType.EPISODE == classify_reference("Frieren E01.mkv")
        assert FileType.EPISODE == classify_reference("Frieren Season 1 E01.mkv")
        assert FileType.SEASON == classify_reference("Season 02")
        assert FileType.TITLE == classify_reference("Frieren (2023)")

    def test_date_compile_strips_trailing_date(self, subtests):
        cases = [
            ("Samurai Champloo (2003)", "Samurai Champloo"),
            ("Kaiju No.9 (2022) (1080p)", "Kaiju No.9 (2022) (1080p)"),
            ("Vanitas no Karte (2020-2026)", "Vanitas no Karte"),
            ("Samurai Champloo", "Samurai Champloo"),
            ("The Emperor's New Groove (2000).mkv", "The Emperor's New Groove (2000).mkv"),
        ]
        for name, expected in cases:
            with subtests.test(name=name):
                assert expected == Generator.DATE_COMPILE.sub("", name).strip()

    def test_cosine_similarity(self, subtests):
        cases = [
            ("identical", [1.0, 0.0], [1.0, 0.0], 1.0),
            ("orthogonal", [1.0, 0.0], [0.0, 1.0], 0.0),
            ("opposite", [1.0, 0.0], [-1.0, 0.0], -1.0),
            ("scaled", [1.0, 2.0], [2.0, 4.0], 1.0),
            ("zero vector", [0.0, 0.0], [1.0, 0.0], 0.0),
            ("both zero", [0.0, 0.0], [0.0, 0.0], 0.0),
        ]
        for label, v1, v2, expected in cases:
            with subtests.test(case=label):
                similarity = cosine_similarity(v1, v2)
                assert not math.isnan(similarity)
                assert expected == pytest.approx(similarity)

    def test_cosine_similarity_rejects_mismatched_dimensions(self):
        v1 = [1.0, 2.0]
        v2 = [1.0, 2.0, 3.0]
        with pytest.raises(ValueError):
            _ = cosine_similarity(v1, v2)

    def test_build_system_prompt_includes_expected_fragments(self, generator, subtests):
        fragments = {
            "extension": (Prompts.EXTENSION.value, {FileType.EPISODE, FileType.TITLE, FileType.MOVIE}),
            "episode": (Prompts.EPISODE.value, {FileType.EPISODE}),
            "season": (Prompts.SEASON.value, {FileType.SEASON}),
            "title": (Prompts.TITLE.value, {FileType.TITLE, FileType.MOVIE}),
            "critical": (Prompts.CRITICAL.value, set(FileType)),
        }
        for filetype in FileType:
            prompt = PromptHelper.build_system_prompt("", filetype)
            for label, (fragment, expected_types) in fragments.items():
                with subtests.test(filetype=filetype.value, fragment=label):
                    if filetype in expected_types:
                        assert fragment in prompt
                    else:
                        assert fragment not in prompt

    def test_build_prompt_includes_title_clause_only_for_episodes_with_title(self, generator, subtests):
        title_name = "Frieren"
        clause = f"\nThe output MUST start with this exact string, character for character: {title_name}"
        for name in (title_name, "", "   "):
            for filetype in FileType:
                with subtests.test(title_name=repr(name), filetype=filetype.value):
                    generator.title_name = name
                    prompt = PromptHelper.build_prompt("Frieren E01.mkv", filetype, title_name=name)
                    expected = filetype == FileType.EPISODE and bool(name.strip())
                    assert expected == (clause in prompt)

    def test_embed_key_varies_with_model_and_prompt(self):
        base = make_embed_key("test_model_a", "ping")
        assert base != make_embed_key("test_model_b", "ping")
        assert base != make_embed_key("test_model_a", "pong")

    def test_blob_roundtrip_preserves_values_as_float32(self):
        vector = [1.5, -2.0, 0.0, 3.25]
        restored = from_blob(to_blob(vector))
        assert restored.dtype == np.float32
        np.testing.assert_allclose(vector, restored)

    def test_open_cache_creates_embeddings_table(self, tmp_path):
        cache_path = tmp_path / "embeddings.sqlite"
        with patch("generator.embed.ollama") as mock_ollama:
            mock_ollama.embeddings.return_value = {"embedding": [1.0, 0.0]}
            _ = Generator(MOCK_CSV, "", "", cache_path=cache_path)

        conn = sqlite3.connect(cache_path)
        try:
            names = {row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            conn.close()
        assert "embeddings" in names

    def test_load_reference_populates_cache_on_miss(self, tmp_path):
        cache_path = tmp_path / "embeddings.sqlite"
        with patch("generator.embed.ollama") as mock_ollama:
            mock_ollama.embeddings.return_value = {"embedding": [1.0, 0.0]}
            gen = Generator(MOCK_CSV, "", "", cache_path=cache_path)
            assert mock_ollama.embeddings.call_count == 3
            assert len(gen.embedder.examples) == 3
        conn = sqlite3.connect(cache_path)
        try:
            count = conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
        finally:
            conn.close()
        assert count == 3

    def test_load_reference_uses_cache_on_second_load(self, tmp_path):
        cache_path = tmp_path / "embeddings.sqlite"
        with patch("generator.embed.ollama") as mock_ollama:
            mock_ollama.embeddings.return_value = {"embedding": [1.0, 0.0]}
            Generator(MOCK_CSV, "", "", cache_path=cache_path)
        with patch("generator.embed.ollama") as mock_ollama:
            mock_ollama.embeddings.return_value = {"embedding": [9.0, 9.0]}
            gen = Generator(MOCK_CSV, "", "", cache_path=cache_path)
            mock_ollama.embeddings.assert_not_called()
        for example in gen.embedder.examples:
            np.testing.assert_allclose([1.0, 0.0], np.asarray(example["vector"]))

    def test_load_reference_without_cache_calls_embeddings_each_time(self, tmp_path):
        with patch("generator.embed.ollama") as mock_ollama, \
                patch.object(EmbedCache, "open", return_value=None):
            mock_ollama.embeddings.return_value = {"embedding": [1.0, 0.0]}
            gen = Generator(MOCK_CSV, "", "", cache_path=tmp_path / "embeddings.sqlite")
            assert mock_ollama.embeddings.call_count == 3
            assert len(gen.embedder.examples) == 3

    def test_load_reference_skips_blank_messy_rows(self, tmp_path):
        csv_path = tmp_path / "with_blank.csv"
        csv_path.write_text(
            "messy_name\tclean_name\n"
            "[EMBER] Kaiju No.9 (2022)\tKaiju No.9 (2022)\n"
            "   \tSeason 02\n"
            "Ep9.mkv\tE09.mkv\n",
            encoding="utf-8")
        with patch("generator.embed.ollama") as mock_ollama:
            mock_ollama.embeddings.return_value = {"embedding": [1.0, 0.0]}
            gen = Generator(csv_path, "", "", cache_path=tmp_path / "embeddings.sqlite")
        assert len(gen.embedder.examples) == 2
        assert mock_ollama.embeddings.call_count == 2

    def test_get_new_name_raises_when_model_returns_prose(self, generator):
        with patch("generator.embed.ollama") as mock_embed_ollama, \
                patch("generator.base.ollama") as mock_base_ollama:
            mock_embed_ollama.embeddings.return_value = {"embedding": [1.0, 0.0]}
            mock_base_ollama.chat.return_value = {
                "message": {"content": "Sure! Here is the cleaned name:\nKaiju No.9 (2022)"}
            }
            with pytest.raises(ModelReturnedProse):
                generator.get_new_name("[EMBER] Kaiju No.9 (2022)", FileType.TITLE)

    def test_get_new_name_accepts_single_line_output(self, generator):
        with patch("generator.embed.ollama") as mock_embed_ollama, \
                patch("generator.base.ollama") as mock_base_ollama:
            mock_embed_ollama.embeddings.return_value = {"embedding": [1.0, 0.0]}
            mock_base_ollama.chat.return_value = {"message": {"content": "  Kaiju No.9 (2022)  "}}
            result = generator.get_new_name("[EMBER] Kaiju No.9 (2022)", FileType.TITLE)
            assert result == "Kaiju No.9 (2022)"
            assert generator.title_name == "Kaiju No.9"
