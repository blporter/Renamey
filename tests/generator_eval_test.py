import re
import pytest

import ollama

from generator import Generator
from models import FileType
from resources import resource_path

TITLE_MODEL = "gemma4:e4b-mlx"
EPISODE_MODEL = "llama3.1:8b"


@pytest.fixture(scope="module")
def generator() -> Generator:
    try:
        ollama.embeddings(model=Generator.EMBED_MODEL, prompt="ping")
    except Exception as e:
        pytest.fail(f"Ollama unavailable: {e}")
    return Generator(csv_path=resource_path("naming_reference.csv"),
                     title_model=TITLE_MODEL,
                     episode_model=EPISODE_MODEL)


@pytest.fixture(autouse=True)
def reset_title_name(generator):
    generator.title_name = ""


class TestGeneratorEval:
    def test_init_loads_references(self, generator: Generator):
        assert len(generator.examples) > 190

    def test_get_references_returns_expected_titles(self, generator: Generator):
        filename = "Long name title"
        references = generator.get_useful_references(filename, FileType.TITLE)
        got_references = []
        for ref in references:
            got_references.append(ref['messy'])
        assert filename == got_references[0]

    def test_get_references_returns_expected_seasons(self, generator: Generator):
        filename = "S01Part1"
        references = generator.get_useful_references(filename, FileType.SEASON)
        got_references = []
        for ref in references:
            got_references.append(ref['messy'])
            assert re.match(r"^Season \d{2}$", ref['clean'])
        assert filename == got_references[0]

    def test_get_references_returns_expected_episodes(self, generator: Generator):
        filename = "Long name title - Season 1 Episode 1.mp4"
        references = generator.get_useful_references(filename, FileType.EPISODE)
        got_references = []
        for ref in references:
            got_references.append(ref['messy'])
        assert filename == got_references[0]

    def test_references_are_stable_across_cached_reload(self, tmp_path):
        cache = tmp_path / "embeddings.sqlite"
        args = dict(csv_path=resource_path("naming_reference.csv"),
                    title_model=TITLE_MODEL, episode_model=EPISODE_MODEL,
                    cache_path=cache)
        first = Generator(**args).get_useful_references("Long name title", FileType.TITLE)
        assert cache.exists()
        second = Generator(**args).get_useful_references("Long name title", FileType.TITLE)
        assert [ref["messy"] for ref in first] == [ref["messy"] for ref in second]

    def test_get_new_name_returns_expected_movies(self, generator: Generator, subtests):
        filenames = [
            "The Emperor's New Groove (2000).mkv",
            "[EMBER] Kaiju No.9 (2022) WEBrip AACx265-EMBER.mp4",
        ]
        expected_names = [
            "The Emperor's New Groove (2000).mkv",
            "Kaiju No.9 (2022).mp4",
        ]
        self.assert_sub_test(subtests, generator, filenames, expected_names, FileType.MOVIE)

    def test_get_new_name_returns_expected_titles(self, generator: Generator, subtests):
        filenames = ["[EMBER] Kaiju No.9 (2022) WEBrip AACx265-EMBER",
                     "[EMBER] Vanitas-no-Karte (2020) 10bit DD 2.0 EDGE2020 WEBrip AAC x265-EMBER",
                     "[Ironclad] Sousou no Frieren - [BD.1080p.AV1] | Frieren: Beyond Journey's End (Multi-Audio, Multi-Subs)",
                     "[Xspitfire911] Samurai Champloo BDRIP 1080p X265 10bit VOSTFR",
                     "[Xspitfire911] Samurai Champloo BDRIP 1080p X265 10bit (2003) VOSTFR",
                     "Heavenly-Delusion.mp4",
                     "Cike-Wu-Liuqi.mov",
                     "The Emperor's New Groove (2000).mkv",
                     "[Erai-raws] Tsue to Tsurugi no Wistoria - [720p CR WEB-DL AVC AAC][MultiSub][5FE7D4DD]"]
        expected_names = ["Kaiju No.9 (2022)",
                          "Vanitas no Karte (2020)",
                          "Sousou no Frieren",
                          "Samurai Champloo",
                          "Samurai Champloo (2003)",
                          "Heavenly Delusion.mp4",
                          "Cike Wu Liuqi.mov",
                          "The Emperor's New Groove (2000).mkv",
                          "Tsue to Tsurugi no Wistoria"]
        self.assert_sub_test(subtests, generator, filenames, expected_names, FileType.TITLE)

    def test_get_new_name_returns_expected_seasons(self, generator: Generator, subtests):
        filenames = [
            "[Anime Time] Hell's Paradise (Jigokuraku) (Season 1) [BD] [Dual Audio][1080p][HEVC 10bit x265][OPUS][Eng Sub] [Batch]",
            "[Erai-raws] Kimi ga Shinu made Koi wo Shitai - S1 [1080p CR WEBRip HEVC AAC][MultiSub][19386605]",
            "[Erai-raws] Yoroi-Shinden Samurai Troopers Part 2 [1080p CR WEBRip HEVC AAC][MultiSub][58DB7293]",
            "[Commie] The Ghost in the Shell - S02 [792D9033].mkv",
            "[Erai-raws] Tsue to Tsurugi no Wistoria 2nd Season - [720p CR WEB-DL AVC AAC][MultiSub][5FE7D4DD]",
            "S01Part1",
            "Season 5",
            "season_06"]
        expected_names = ["Season 01",
                          "Season 01",
                          "Season 02",
                          "Season 02",
                          "Season 02",
                          "Season 01",
                          "Season 05",
                          "Season 06"]
        self.assert_sub_test(subtests, generator, filenames, expected_names, FileType.SEASON)

    def test_get_new_name_returns_expected_episodes(self, generator: Generator, subtests):
        filenames = [
            "[Yameii] Witch Hat Atelier - S01E11 [English Dub] [CR WEB-DL 1080p H264 AAC] [DC7B989F] (Tongari Boushi no Atelier).mp4",
            "[Erai-raws] Digimon Beatbreak - 43 [1080p CR WEBRip HEVC AAC][MultiSub][BB4236AA].mkv",
            "Ep9.mkv",
            "Episode 10",
            "E12.png"]
        expected_names = ["Witch Hat Atelier E11.mp4",
                          "Digimon Beatbreak E43.mkv",
                          "E09.mkv",
                          "E10",
                          "E12.png"]
        self.assert_sub_test(subtests, generator, filenames, expected_names, FileType.EPISODE)

    def test_get_new_name_returns_expected_episodes_with_existing_title(self, generator, subtests):
        filenames = [
            "[Erai-raws] Tsue to Tsurugi no Wistoria (2025) 2nd Season - 12 [720p CR WEB-DL AVC AAC][MultiSub][5FE7D4DD]",
            "[Yameii] Witch Hat Atelier - S01E11 [English Dub] [CR WEB-DL 1080p H264 AAC] [DC7B989F] (Tongari Boushi no Atelier).mp4",
            "[Erai-raws] Digimon Beatbreak - 43 [1080p CR WEBRip HEVC AAC][MultiSub][BB4236AA].mkv",
            "[DB]Vanitas no Karte_2022_-_02_(Dual Audio_10bit_BD1080p_x265).mov",
            "E12.mkv"]
        titles = ["Tsue to Tsurugi no Wistoria",
                  "Witch Hat Atelier",
                  "Digimon Beatbreak",
                  "Vanitas no Karte",
                  "Kaiju No.8"]
        expected_names = ["Tsue to Tsurugi no Wistoria E12",
                          "Witch Hat Atelier E11.mp4",
                          "Digimon Beatbreak E43.mkv",
                          "Vanitas no Karte E02.mov",
                          "Kaiju No.8 E12.mkv"]
        self.assert_sub_test(subtests, generator, filenames, expected_names, FileType.EPISODE, titles=titles)

    def test_get_new_name_saves_title_and_returns_expected_episodes(self, generator: Generator, subtests):
        filenames = [
            "[Erai-raws] Tsue to Tsurugi no Wistoria (2025) [720p CR WEB-DL AVC AAC][MultiSub][5FE7D4DD]",
            "[Yameii] Witch Hat Atelier - [English Dub] [CR WEB-DL 1080p H264 AAC] [DC7B989F] (Tongari Boushi no Atelier)",
            "[DB]Vanitas no Karte_2022_-_(Dual Audio_10bit_BD1080p_x265)"]
        expected_titles = ["Tsue to Tsurugi no Wistoria",
                           "Witch Hat Atelier",
                           "Vanitas no Karte"]
        episodes = ["E01.mkv", "Episode 5", "E7.mp4"]
        expected_episodes = ["E01.mkv", "E05", "E07.mp4"]

        for title_input, expected_title in zip(filenames, expected_titles):
            with subtests.test(title=title_input):
                generator.get_new_name(title_input, FileType.TITLE)
                assert expected_title == generator.title_name
            for episode, expected_episode in zip(episodes, expected_episodes):
                with subtests.test(title=expected_title, episode=episode):
                    got = generator.get_new_name(episode, FileType.EPISODE)
                    assert f"{expected_title} {expected_episode}" == got

    @staticmethod
    def assert_sub_test(subtests, generator: Generator, filenames: list[str], expected_names: list[str],
                        file_type: FileType, titles=None):
        for i, (name, expected) in enumerate(zip(filenames, expected_names)):
            with subtests.test(name=name):
                if titles is not None:
                    generator.title_name = titles[i]
                assert expected == generator.get_new_name(name, file_type)
