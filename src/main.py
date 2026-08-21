import argparse
import json
import os
import re
from enum import Enum
from pathlib import Path

from generator import Generator


class FileType(Enum):
    TITLE = "title"
    SEASON = "season"
    EPISODE = "episode"


class FileParser:
    gen = Generator(Path.cwd() / "naming_reference.csv")
    ignore_set = []

    def __init__(self):
        self.ignore_set = self.build_ignore_set()

    @staticmethod
    def build_ignore_set() -> set:
        ignore_path = Path.cwd() / "ignore_list.json"
        with open(ignore_path, "r") as file:
            config = json.load(file)
            return set(config.get("ignore_files", []))

    @staticmethod
    def get_path_from_args() -> Path:
        parser = argparse.ArgumentParser(description="Process a folder or file's absolute filepath.")
        parser.add_argument('-f', '--filepath', type=str, required=True)
        args = parser.parse_args()

        filepath = Path(os.path.expandvars(args.filepath)).expanduser()
        if not filepath.is_absolute():
            filepath = Path.cwd() / Path(filepath)

        if not filepath.exists():
            raise argparse.ArgumentTypeError(f"{args.filepath} does not exist.")

        return filepath

    def get_new_path(self, filepath: Path, filetype: FileType) -> Path:
        path_prefix = filepath.parent
        cleaned_path_name = re.sub(r'[<>:\"/\\|?*]', '', filepath.name)
        new_name = self.gen.get_new_name(cleaned_path_name, filetype.value)
        return path_prefix / new_name

    def handle_nested_folders(self, filepath: Path):
        if filepath.name in self.ignore_set:
            return
        if filepath.is_dir():
            folder_path = self.get_new_path(filepath, FileType.SEASON)
            os.rename(filepath, folder_path)
            for file in folder_path.iterdir():
                self.handle_nested_folders(file)
        else:
            new_file = self.get_new_path(filepath, FileType.EPISODE)
            os.rename(filepath, new_file)


def main():
    parser = FileParser()
    filepath = parser.get_path_from_args()
    new_path = parser.get_new_path(filepath, FileType.TITLE)
    os.rename(filepath, new_path)
    if new_path.is_dir():
        for file in new_path.iterdir():
            parser.handle_nested_folders(file)


if __name__ == '__main__':
    main()
