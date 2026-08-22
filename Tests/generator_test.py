import re
import unittest
from pathlib import Path

from src.generator import Generator
from src.models import FileType


class TestGeneratorMethods(unittest.TestCase):
    TITLE_MODEL = "gemma4:e4b-mlx"
    EPISODE_MODEL = "llama3.1:8b"

    @classmethod
    def setUpClass(cls):
        cls.generator = Generator(csv_path=Path.cwd().parent / "naming_reference.csv",
                                  title_model=cls.TITLE_MODEL,
                                  episode_model=cls.EPISODE_MODEL)

    def setUp(self):
        self.generator.title_name = ""

    def test_init_loads_references(self):
        self.assertGreater(len(self.generator.examples), 100)

    def test_get_references_returns_expected_titles(self):
        filename = "Long name title"
        references = self.generator.get_useful_references(filename, FileType.TITLE)
        got_references = []
        for ref in references:
            got_references.append(ref['messy'])
        self.assertEqual(filename, got_references[0])

    def test_get_references_returns_expected_seasons(self):
        filename = "S01Part1"
        references = self.generator.get_useful_references(filename, FileType.SEASON)
        got_references = []
        for ref in references:
            got_references.append(ref['messy'])
            self.assertTrue(re.match(r"^Season \d{2}$", ref['clean']))
        self.assertEqual(filename, got_references[0])

    def test_get_references_returns_expected_episodes(self):
        filename = "Long name title - Season 1 Episode 1.mp4"
        references = self.generator.get_useful_references(filename, FileType.EPISODE)
        got_references = []
        for ref in references:
            got_references.append(ref['messy'])
        self.assertEqual(filename, got_references[0])

    def test_get_new_name_returns_expected_titles(self):
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
        got_names = []
        for name in filenames:
            got_names.append(self.generator.get_new_name(name, FileType.TITLE))
        self.assertEqual(expected_names, got_names)

    def test_get_new_name_returns_expected_seasons(self):
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
        got_names = []
        for name in filenames:
            got_names.append(self.generator.get_new_name(name, FileType.SEASON))
        self.assertEqual(expected_names, got_names)

    def test_get_new_name_returns_expected_episodes(self):
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
        got_names = []
        for name in filenames:
            got_names.append(self.generator.get_new_name(name, FileType.EPISODE))
        self.assertEqual(expected_names, got_names)

    def test_get_new_name_returns_expected_episodes_with_existing_title(self):
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
        got_names = []
        for i, name in enumerate(filenames):
            self.generator.title_name = titles[i]
            got_names.append(self.generator.get_new_name(name, FileType.EPISODE))
        self.assertEqual(expected_names, got_names)

    def test_get_new_name_saves_title_and_returns_expected_episodes(self):
        filenames = [
            "[Erai-raws] Tsue to Tsurugi no Wistoria (2025) [720p CR WEB-DL AVC AAC][MultiSub][5FE7D4DD]",
            "[Yameii] Witch Hat Atelier - [English Dub] [CR WEB-DL 1080p H264 AAC] [DC7B989F] (Tongari Boushi no Atelier)",
            "[DB]Vanitas no Karte_2022_-_(Dual Audio_10bit_BD1080p_x265)"]
        episodes = ["E01.mkv", "Episode 5", "E7.mp4"]
        expected_titles = ["Tsue to Tsurugi no Wistoria",
                           "Witch Hat Atelier",
                           "Vanitas no Karte"]
        expected_episodes = ["E01.mkv", "E05", "E07.mp4"]
        for i, name in enumerate(filenames):
            self.generator.get_new_name(name, FileType.TITLE)
            self.assertEqual(expected_titles[i], self.generator.title_name)
            for j, episode in enumerate(episodes):
                got_episode = self.generator.get_new_name(episode, FileType.EPISODE)
                self.assertEqual(f"{expected_titles[i]} {expected_episodes[j]}", got_episode)


if __name__ == '__main__':
    unittest.main()
