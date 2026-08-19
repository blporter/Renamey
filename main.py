import argparse
import os
from enum import Enum
from pathlib import Path

from generator import Generator

gen = Generator()


class FileType(Enum):
    TITLE = "title"
    SEASON = "season"
    EPISODE = "episode"


def arg_parser() -> Path:
    parser = argparse.ArgumentParser(description="Process a folder or file's absolute filepath.")
    parser.add_argument('-f', '--filepath', type=str, required=True)
    args = parser.parse_args()

    filepath = Path(os.path.expandvars(args.filepath)).expanduser()
    if not filepath.is_absolute():
        filepath = Path.cwd() / Path(filepath)

    if not filepath.exists():
        raise argparse.ArgumentTypeError(f"{args.filepath} does not exist.")

    return filepath


def get_new_path(filepath: Path, filetype: FileType) -> Path:
    path_prefix = filepath.parent
    new_name = gen.get_new_name(filepath.name, filetype.value)
    return path_prefix / new_name


def handle_nested_folders(filepath: Path):
    if filepath.name == ".DS_Store":
        return
    if filepath.is_dir():
        folder_path = get_new_path(filepath, FileType.SEASON)
        os.rename(filepath, folder_path)
        for file in folder_path.iterdir():
            handle_nested_folders(file)
    else:
        new_file = get_new_path(filepath, FileType.EPISODE)
        os.rename(filepath, new_file)


def main():
    filepath = arg_parser()
    new_path = get_new_path(filepath, FileType.TITLE)
    os.rename(filepath, new_path)
    if new_path.is_dir():
        for file in new_path.iterdir():
            handle_nested_folders(file)


if __name__ == '__main__':
    main()
