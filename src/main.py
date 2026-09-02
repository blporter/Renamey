import re
from pathlib import Path
from argparse import ArgumentTypeError

import logging

from generator import Generator
from manifest import ManifestLogger
from parser import FileParser
from models import FileType, ContentType
from resources import resource_path

logging.basicConfig(level=logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


def create_season_folder(mani: ManifestLogger, filepath: Path, season_name: str):
    mani.log_mkdir(filepath / season_name)
    logging.info(f"Created season folder at {filepath / season_name}")
    for file in filepath.iterdir():
        if file.is_file():
            target_path = filepath / season_name / file.name
            mani.log_move(file, target_path)
            logging.debug(f"Moved {file.name} to {target_path.name}")


def get_new_path(gen: Generator, filepath: Path, filetype: FileType) -> Path:
    cleaned_path_name = re.sub(r'[<>:\"/\\|?*]', '', filepath.name)
    logging.debug(f"File name after cleaning: {cleaned_path_name}")
    try:
        new_name = gen.get_new_name(cleaned_path_name, filetype)
    except ValueError as e:
        logging.warning(f"Failed to generate new name for {filepath.name}: {e}")
        new_name = filepath.name
    return filepath.parent / new_name


def handle_nested_folders(gen: Generator, mani: ManifestLogger, content_type: ContentType, ignore_set: set,
                          filepath: Path, dry_run):
    if filepath.name in ignore_set:
        logging.debug(f"Skipping ignored file: {filepath.name}")
        return
    if content_type == ContentType.SHOW:
        if filepath.is_dir():
            folder_path = get_new_path(gen, filepath, FileType.SEASON)
            print(f"\t├── Season: {filepath.name} --> {folder_path.name}")
            if not dry_run:
                mani.log_move(filepath, folder_path)
                filepath = folder_path
            for file in filepath.iterdir():
                handle_nested_folders(gen, mani, content_type, ignore_set, file, dry_run)
        else:
            new_file = get_new_path(gen, filepath, FileType.EPISODE)
            print(f"\t│\t├── Episode: {filepath.name} --> {new_file.name}")
            if not dry_run:
                mani.log_move(filepath, new_file)
    if content_type == ContentType.MOVIE:
        new_file = get_new_path(gen, filepath, FileType.TITLE)
        print(f"\t├── Movie: {filepath.name} --> {new_file.name}")
        if not dry_run:
            mani.log_move(filepath, new_file)


def main():
    parser = FileParser()
    try:
        args = parser.get_parts_from_args()
        if isinstance(args, bool):
            # TODO
            print("undo prior changes")
            return
        else:
            content_type, filepath, title_model, episode_model, dry_run = args
    except ArgumentTypeError as e:
        print(f"Failed to parse arguments: {e}")
        return
    gen = Generator(resource_path("naming_reference.csv"), title_model, episode_model)
    mani = ManifestLogger(content_type, filepath, dry_run)

    if content_type == ContentType.SHOW:
        if not any(file.is_dir() for file in filepath.iterdir()) and not dry_run:
            print(f"Season folder not found, creating one and moving contents to it")
            season_folder = get_new_path(gen, filepath, FileType.SEASON)
            create_season_folder(mani, filepath, season_folder.name)

    new_path = get_new_path(gen, filepath, FileType.TITLE)
    print(f"Title: {filepath.name} --> {new_path.name}")
    if not dry_run:
        mani.log_move(filepath, new_path)
        filepath = new_path

    try:
        ignore_set = parser.build_ignore_set(resource_path("ignore_list.json"))
    except (OSError, ValueError, AttributeError, TypeError) as e:
        logging.warning(f"Could not load ignore list: {e}. Ignoring nothing.")
        ignore_set = set()
    if filepath.is_dir():
        for file in filepath.iterdir():
            handle_nested_folders(gen, mani, content_type, ignore_set, file, dry_run)
    if not dry_run:
        mani.log_complete()


if __name__ == '__main__':
    main()
