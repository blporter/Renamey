import math
import unittest

from pathlib import Path
from unittest.mock import patch

from generator import Generator
from models import FileType, Prompts


class TestGeneratorMethods(unittest.TestCase):
    MOCK_CSV = Path(__file__).resolve().parent / "mock_reference.csv"

    @classmethod
    def setUpClass(cls):
        with patch("generator.ollama") as mock_ollama:
            mock_ollama.embeddings.return_value = {"embedding": [1.0, 0.0]}
            cls.generator = Generator(cls.MOCK_CSV, "", "")

    def setUp(self):
        self.generator.title_name = ""

    def test_classify_returns_expected_filetypes(self):
        self.assertEqual(FileType.EPISODE, Generator.classify("Frieren E01.mkv"))
        self.assertEqual(FileType.EPISODE, Generator.classify("Frieren Season 1 E01.mkv"))
        self.assertEqual(FileType.SEASON, Generator.classify("Season 02"))
        self.assertEqual(FileType.TITLE, Generator.classify("Frieren (2023)"))

    def test_date_compile_strips_trailing_date(self):
        cases = [
            ("Samurai Champloo (2003)", "Samurai Champloo"),
            ("Kaiju No.9 (2022) (1080p)", "Kaiju No.9 (2022) (1080p)"),
            ("Vanitas no Karte (2020-2026)", "Vanitas no Karte"),
            ("Samurai Champloo", "Samurai Champloo"),
            ("The Emperor's New Groove (2000).mkv", "The Emperor's New Groove (2000).mkv"),
        ]
        for name, expected in cases:
            with self.subTest(name=name):
                self.assertEqual(expected, Generator.DATE_COMPILE.sub("", name).strip())

    def test_cosine_similarity(self):
        cases = [
            ("identical", [1.0, 0.0], [1.0, 0.0], 1.0),
            ("orthogonal", [1.0, 0.0], [0.0, 1.0], 0.0),
            ("opposite", [1.0, 0.0], [-1.0, 0.0], -1.0),
            ("scaled", [1.0, 2.0], [2.0, 4.0], 1.0),
            ("zero vector", [0.0, 0.0], [1.0, 0.0], 0.0),
            ("both zero", [0.0, 0.0], [0.0, 0.0], 0.0),
        ]
        for label, v1, v2, expected in cases:
            with self.subTest(case=label):
                similarity = Generator.cosine_similarity(v1, v2)
                self.assertFalse(math.isnan(similarity))
                self.assertAlmostEqual(expected, similarity)

    def test_cosine_similarity_rejects_mismatched_dimensions(self):
        v1 = [1.0, 2.0]
        v2 = [1.0, 2.0, 3.0]
        with self.assertRaises(ValueError):
            _ = Generator.cosine_similarity(v1, v2)

    def test_build_system_prompt_includes_expected_fragments(self):
        fragments = {
            "extension": (Prompts.EXTENSION.value, {FileType.EPISODE, FileType.TITLE}),
            "episode": (Prompts.EPISODE.value, {FileType.EPISODE}),
            "season": (Prompts.SEASON.value, {FileType.SEASON}),
            "title": (Prompts.TITLE.value, {FileType.TITLE}),
            "critical": (Prompts.CRITICAL.value, set(FileType)),
        }
        for filetype in FileType:
            prompt = self.generator.build_system_prompt("", filetype)
            for label, (fragment, expected_types) in fragments.items():
                with self.subTest(filetype=filetype.value, fragment=label):
                    if filetype in expected_types:
                        self.assertIn(fragment, prompt)
                    else:
                        self.assertNotIn(fragment, prompt)

    def test_build_prompt_includes_title_clause_only_for_episodes_with_title(self):
        title_name = "Frieren"
        clause = f"\nThe output MUST start with this exact string, character for character: {title_name}"
        for name in (title_name, "", "   "):
            for filetype in FileType:
                with self.subTest(title_name=repr(name), filetype=filetype.value):
                    self.generator.title_name = name
                    prompt = self.generator.build_prompt("Frieren E01.mkv", filetype)
                    expected = filetype == FileType.EPISODE and bool(name.strip())
                    self.assertEqual(expected, clause in prompt)
