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
logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_new_path(gen: Generator, filepath: Path, filetype: FileType) -> Path:
    path_prefix = filepath.parent
    cleaned_path_name = re.sub(r'[<>:\"/\\|?*]', '', filepath.name)
    logging.debug(f"File name after cleaning: {cleaned_path_name}")
    new_name = gen.get_new_name(cleaned_path_name, filetype)
    return path_prefix / new_name


def handle_nested_folders(gen: Generator, ignore_set: set, filepath: Path, dry_run):
    if filepath.name in ignore_set:
        logging.debug(f"Skipping ignored file: {filepath.name}")
        return
    if filepath.is_dir():
        folder_path = get_new_path(gen, filepath, FileType.SEASON)
        print(f"Season: {filepath.name} -> {folder_path.name}")
        if not dry_run:
            os.rename(filepath, folder_path)
            filepath = folder_path
        for file in filepath.iterdir():
            handle_nested_folders(gen, ignore_set, file, dry_run)
    else:
        new_file = get_new_path(gen, filepath, FileType.EPISODE)
        print(f"Episode: {filepath.name} -> {new_file.name}")
        if not dry_run:
            os.rename(filepath, new_file)


def main():
    parser = FileParser()
    try:
        filepath, title_model, episode_model, dry_run = parser.get_parts_from_args()
    except ArgumentTypeError as e:
        print(f"Failed to parse arguments: {e}")
        return
    gen = Generator(Path.cwd() / "naming_reference.csv", title_model, episode_model)

    new_path = get_new_path(gen, filepath, FileType.TITLE)
    print(f"Title: {filepath.name} -> {new_path.name}")
    if not dry_run:
        os.rename(filepath, new_path)
        filepath = new_path

    ignore_set = parser.build_ignore_set()
    if filepath.is_dir():
        for file in filepath.iterdir():
            handle_nested_folders(gen, ignore_set, file, dry_run)


if __name__ == '__main__':
    main()
