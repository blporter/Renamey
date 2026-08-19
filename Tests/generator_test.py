import unittest

from generator import Generator


class TestGeneratorMethods(unittest.TestCase):

    def setUp(self):
        self.generator = Generator(csv_file="../naming_reference.csv")

    def test_init_loads_references(self):
        gen = Generator(csv_file="../naming_reference.csv")
        self.assertGreater(len(gen.examples), 100)

    def test_get_references_returns_expected_titles(self):
        filename = "Long name title"
        filetype = "title"
        expected_references = ["Long name title",
                               "Long name title - Season 1",
                               "Long name title - S02 E01.mov",
                               "Long name title - Season 1 Episode 1.mp4"]
        references = self.generator.get_useful_references(filename, filetype)
        got_references = []
        for ref in references:
            got_references.append(ref['messy'])
        self.assertEqual(expected_references, got_references)

    def test_get_references_returns_expected_seasons(self):
        filename = "Long name title - Season 1"
        filetype = "season"
        expected_references = ["Long name title - Season 1",
                               "Long name title"]
        references = self.generator.get_useful_references(filename, filetype)
        got_references = []
        for ref in references:
            got_references.append(ref['messy'])
        self.assertEqual(expected_references, got_references)

    def test_get_references_returns_expected_episodes(self):
        filename = "Long name title - Season 1 Episode 1.mp4"
        filetype = "episode"
        expected_references = ["Long name title - Season 1 Episode 1.mp4",
                               "Long name title - Season 1"]
        references = self.generator.get_useful_references(filename, filetype)
        got_references = []
        for ref in references:
            got_references.append(ref['messy'])
        self.assertEqual(expected_references, got_references)

    def test_get_new_name_returns_expected_titles(self):
        filenames = ["[EMBER] Kaiju No.9 (2022) WEBrip AACx265-EMBER",
                     "[EMBER] Vanitas-no-Karte (2020) 10bit DD 2.0 EDGE2020 WEBrip AAC x265-EMBER",
                     "[Ironclad] Sousou no Frieren - [BD.1080p.AV1] | Frieren: Beyond Journey's End (Multi-Audio, Multi-Subs)",
                     "[Xspitfire911] Samurai Champloo BDRIP 1080p X265 10bit VOSTFR",
                     "Heavenly-Delusion.mp4",
                     "Cike-Wu-Liuqi.mov",
                     "The Emperor's New Groove (2000).mkv"]
        filetype = "title"
        expected_names = ["kaiju_no_9", "vanitas_no_karte", "sousou_no_frieren", "samurai_champloo", "heavenly_delusion.mp4", "cike_wu_liuqi.mov", "the_emperors_new_groove.mkv"]
        got_names = []
        for name in filenames:
            got_names.append(self.generator.get_new_name(name, filetype))
        self.assertEqual(expected_names, got_names)

    def test_get_new_name_returns_expected_seasons(self):
        filenames = ["[Anime Time] Hell's Paradise (Jigokuraku) (Season 1) [BD] [Dual Audio][1080p][HEVC 10bit x265][OPUS][Eng Sub] [Batch]",
                     "[Erai-raws] Kimi ga Shinu made Koi wo Shitai - S1 [1080p CR WEBRip HEVC AAC][MultiSub][19386605]",
                     "[Erai-raws] Yoroi-Shinden Samurai Troopers Part 2 [1080p CR WEBRip HEVC AAC][MultiSub][58DB7293]",
                     "[Commie] The Ghost in the Shell - S02 [792D9033].mkv",
                     "S01Part1",
                     "Season 5",
                     "season_06"]
        filetype = "season"
        expected_names = ["season_01", "season_01", "season_02", "season_02", "season_01", "season_05", "season_06"]
        got_names = []
        for name in filenames:
            got_names.append(self.generator.get_new_name(name, filetype))
        self.assertEqual(expected_names, got_names)

    def test_get_new_name_returns_expected_episodes(self):
        filenames = ["[Erai-raws] Tsue to Tsurugi no Wistoria 2nd Season - 12 [720p CR WEB-DL AVC AAC][MultiSub][5FE7D4DD]",
                     "[Yameii] Witch Hat Atelier - S01E11 [English Dub] [CR WEB-DL 1080p H264 AAC] [DC7B989F] (Tongari Boushi no Atelier).mp4",
                     "[Erai-raws] Digimon Beatbreak - 43 [1080p CR WEBRip HEVC AAC][MultiSub][BB4236AA].mkv",
                     "[DB]Vanitas no Karte_-_02_(Dual Audio_10bit_BD1080p_x265).mov",
                     "Ep9.mkv",
                     "Episode 10",
                     "E12.png"]
        filetype = "episode"
        expected_names = ["episode_12", "episode_11.mp4", "episode_43.mkv", "episode_02.mov", "episode_09.mkv", "episode_10", "episode_12.png"]
        got_names = []
        for name in filenames:
            got_names.append(self.generator.get_new_name(name, filetype))
        self.assertEqual(expected_names, got_names)


if __name__ == '__main__':
    unittest.main()
