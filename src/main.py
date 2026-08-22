import os
import re
from pathlib import Path
from argparse import ArgumentTypeError

import logging

from generator import Generator
from parser import FileParser
from models import FileType

logging.basicConfig(level=logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)


def get_new_path(gen: Generator, filepath: Path, filetype: FileType) -> Path:
    path_prefix = filepath.parent
    cleaned_path_name = re.sub(r'[<>:\"/\\|?*]', '', filepath.name)
    new_name = gen.get_new_name(cleaned_path_name, filetype)
    return path_prefix / new_name


def handle_nested_folders(gen: Generator, ignore_set: set, filepath: Path):
    if filepath.name in ignore_set:
        logging.debug(f"Skipping ignored file: {filepath.name}")
        return
    if filepath.is_dir():
        folder_path = get_new_path(gen, filepath, FileType.SEASON)
        os.rename(filepath, folder_path)
        logging.info(f"Renamed season folder: {filepath} -> {folder_path}")
        for file in folder_path.iterdir():
            handle_nested_folders(gen, ignore_set, file)
    else:
        new_file = get_new_path(gen, filepath, FileType.EPISODE)
        os.rename(filepath, new_file)
        logging.info(f"Renamed episode: {filepath} -> {new_file}")


def main():
    parser = FileParser()
    try:
        filepath, title_model, episode_model = parser.get_parts_from_args()
    except ArgumentTypeError as e:
        print(f"Failed to parse arguments: {e}")
        return
    gen = Generator(Path.cwd() / "naming_reference.csv", title_model, episode_model)

    new_path = get_new_path(gen, filepath, FileType.TITLE)
    os.rename(filepath, new_path)
    logging.info(f"Renamed title: {filepath} -> {new_path}")

    ignore_set = parser.build_ignore_set()
    if new_path.is_dir():
        for file in new_path.iterdir():
            handle_nested_folders(gen, ignore_set, file)


if __name__ == '__main__':
    main()
