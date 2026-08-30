import os
import re
import shutil
from pathlib import Path
from argparse import ArgumentTypeError

import logging

from generator import Generator
from parser import FileParser
from models import FileType, ContentType
from resources import resource_path

logging.basicConfig(level=logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


def create_season_folder(filepath: Path):
    with_season = filepath / (filepath.name + " Season")
    try:
        with_season.mkdir(parents=False, exist_ok=True)
    except FileNotFoundError as e:
        logging.warning(f"Skipping season directory, problem with structure: {e}")
        return
    for file in filepath.iterdir():
        if file.is_file():
            target_path = with_season / file.name
            shutil.move(str(file), str(target_path))


def get_new_path(gen: Generator, filepath: Path, filetype: FileType) -> Path:
    cleaned_path_name = re.sub(r'[<>:\"/\\|?*]', '', filepath.name)
    logging.debug(f"File name after cleaning: {cleaned_path_name}")
    try:
        new_name = gen.get_new_name(cleaned_path_name, filetype)
    except ValueError as e:
        logging.warning(f"Failed to generate new name for {filepath.name}: {e}")
        new_name = filepath.name
    return filepath.parent / new_name


def handle_nested_folders(gen: Generator, content_type: ContentType, ignore_set: set, filepath: Path, dry_run):
    if filepath.name in ignore_set:
        logging.debug(f"Skipping ignored file: {filepath.name}")
        return
    if content_type == ContentType.SHOW:
        if filepath.is_dir():
            folder_path = get_new_path(gen, filepath, FileType.SEASON)
            print(f"\t├── Season: {filepath.name} --> {folder_path.name}")
            if not dry_run:
                os.rename(filepath, folder_path)
                filepath = folder_path
            for file in filepath.iterdir():
                handle_nested_folders(gen, content_type, ignore_set, file, dry_run)
        else:
            new_file = get_new_path(gen, filepath, FileType.EPISODE)
            print(f"\t│\t├── Episode: {filepath.name} --> {new_file.name}")
            if not dry_run:
                os.rename(filepath, new_file)
    if content_type == ContentType.MOVIE:
        new_file = get_new_path(gen, filepath, FileType.TITLE)
        print(f"\t├── Movie: {filepath.name} --> {new_file.name}")
        if not dry_run:
            os.rename(filepath, new_file)


def main():
    parser = FileParser()
    try:
        content_type, filepath, title_model, episode_model, dry_run = parser.get_parts_from_args()
    except ArgumentTypeError as e:
        print(f"Failed to parse arguments: {e}")
        return
    gen = Generator(resource_path("naming_reference.csv"), title_model, episode_model)

    new_path = get_new_path(gen, filepath, FileType.TITLE)
    print(f"Title: {filepath.name} --> {new_path.name}")
    if not dry_run:
        os.rename(filepath, new_path)
        filepath = new_path

    if content_type == ContentType.SHOW:
        if not any(file.is_dir() for file in filepath.iterdir()) and not dry_run:
            print(f"Season folder not found, creating one and moving contents to it")
            create_season_folder(filepath)

    try:
        ignore_set = parser.build_ignore_set(resource_path("ignore_list.json"))
    except (OSError, ValueError, AttributeError, TypeError) as e:
        logging.warning(f"Could not load ignore list: {e}. Ignoring nothing.")
        ignore_set = set()
    if filepath.is_dir():
        for file in filepath.iterdir():
            handle_nested_folders(gen, content_type, ignore_set, file, dry_run)


if __name__ == '__main__':
    main()
