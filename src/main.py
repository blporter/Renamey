import re
from pathlib import Path
from argparse import ArgumentTypeError

import logging

import ollama

from errors import ManifestAlreadyInProgress
from generator import Generator
from manifest import ManifestLogger
from parser import FileParser
from models import FileType, ContentType, ManifestStatus, ManifestOperation
from resources import resource_path, default_manifest_path, open_existing_manifest
from undoer import Undoer

logging.basicConfig(level=logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


class Renamey:
    gen: Generator
    mani: ManifestLogger
    ignore_set: set[str]
    content_type: ContentType
    filepath: Path
    dry_run: bool

    def __init__(self, args, ignore_set: set[str]):
        self.ignore_set = ignore_set
        self.content_type, self.filepath, title_model, episode_model, self.dry_run, self.resume = args
        self.gen = Generator(resource_path("naming_reference.csv"), title_model, episode_model)

    @staticmethod
    def perform_undo():
        try:
            undoer = Undoer()
            undoer.undo_manifest()
            ManifestLogger.pretty_print(undoer.manifest, reverse=True)
        except (ValueError, KeyError, Exception) as e:
            logging.critical(f"Failed to undo: {e}")

    def run(self):
        existing_manifest = open_existing_manifest(default_manifest_path())
        if existing_manifest and existing_manifest["status"] == ManifestStatus.IN_PROGRESS.value:
            if self.resume:
                if existing_manifest["operations"][-1]["status"] == ManifestStatus.IN_PROGRESS.value:
                    if not self.dry_run:
                        undoer = Undoer.from_manifest(existing_manifest)
                        undoer.undo_last_operation()
                    else:
                        existing_manifest["operations"].pop()
            else:
                raise ManifestAlreadyInProgress(str(default_manifest_path()))
        try:
            self.mani = ManifestLogger(self.content_type, self.filepath, self.dry_run)
        except Exception as e:
            logging.critical(f"Failed to create manifest: {e}")
            return

        if self.resume and self.mani.manifest["operations"]:
            first_op = self.mani.manifest["operations"][0]
            if first_op["op_type"] == ManifestOperation.MOVE.value and first_op["filetype"] == FileType.TITLE.value and \
                    first_op["status"] == ManifestStatus.COMPLETE.value:
                self.gen.title_name = Generator.DATE_COMPILE.sub("", self.filepath.name).strip()
        self.perform_rename()

    def perform_rename(self):
        original_name = self.filepath.name
        new_path = self.get_new_path(self.filepath, FileType.TITLE)
        self.mani.log_move(self.filepath, new_path, FileType.TITLE)
        logical_path = new_path
        if not self.dry_run:
            self.filepath = new_path

        should_skip_nested = self.handle_season_with_no_folder(self.filepath, logical_path, original_name)

        if not should_skip_nested and self.filepath.is_dir():
            for file in self.filepath.iterdir():
                child_path = logical_path / file.name
                self.handle_nested_folders(file, child_path)

        self.mani.log_complete()
        ManifestLogger.pretty_print(self.mani.manifest)

    def handle_season_with_no_folder(self, filepath: Path, logical_path: Path, original_name: str) -> bool:
        if self.content_type == ContentType.SHOW:
            if not any(file.is_dir() for file in filepath.iterdir()):
                season_name = original_name + " (New Dir)"
                season_path = logical_path / season_name
                loose_files = [file for file in filepath.iterdir() if file.is_file()]
                self.mani.log_mkdir(season_path, filetype=FileType.SEASON)
                self.move_episodes_into_season(filepath, logical_path, season_name)

                new_season = self.get_new_path(season_path, FileType.SEASON)
                self.mani.log_move(season_path, new_season, FileType.SEASON)

                for file in loose_files:
                    if file.name not in self.ignore_set:
                        episode_logical_path = new_season / file.name
                        new_episode = self.get_new_path(episode_logical_path, FileType.EPISODE)
                        self.mani.log_move(episode_logical_path, new_episode, FileType.EPISODE)
                return True
        return False

    def move_episodes_into_season(self, filepath: Path, logical_path: Path, season_name: str):
        logging.info(f"Moving all episodes into new season folder {season_name}")
        for file in filepath.iterdir():
            if file.is_file():
                target_path = logical_path / season_name / file.name
                self.mani.log_move(logical_path / file.name, target_path, filetype=FileType.EPISODE)
                logging.debug(f"Moved {file.name} to {target_path.name}")

    def get_new_path(self, filepath: Path, filetype: FileType) -> Path:
        key = str(filepath)
        if key in self.mani.completed_moves:
            logging.debug(f"Skipping already completed move: {key}")
            return Path(self.mani.completed_moves[key])
        cleaned_path_name = re.sub(r'[<>:\"/\\|?*]', '', filepath.name)
        logging.debug(f"File name after cleaning: {cleaned_path_name}")
        try:
            new_name = self.gen.get_new_name(cleaned_path_name, filetype)
        except ValueError as e:
            logging.error(f"Failed to generate new name for {filepath.name}: {e}")
            new_name = filepath.name
        return filepath.parent / new_name

    def handle_nested_folders(self, filepath: Path, logical_path: Path):
        if filepath.name in self.ignore_set:
            logging.debug(f"Skipping ignored file: {filepath.name}")
            return

        if self.content_type == ContentType.SHOW:
            if filepath.is_dir():
                new_logical_path = self.get_new_path(logical_path, FileType.SEASON)
                self.mani.log_move(logical_path, new_logical_path, FileType.SEASON)
                if not self.dry_run:
                    filepath = new_logical_path
                for file in filepath.iterdir():
                    child_path = new_logical_path / file.name
                    self.handle_nested_folders(file, child_path)
            else:
                new_file = self.get_new_path(logical_path, FileType.EPISODE)
                self.mani.log_move(logical_path, new_file, FileType.EPISODE)

        if self.content_type == ContentType.MOVIE:
            new_file = self.get_new_path(logical_path, FileType.MOVIE)
            self.mani.log_move(logical_path, new_file, FileType.MOVIE)


def main():
    try:
        ollama.list()
    except Exception as e:
        logging.critical(f"Ollama unavailable: {e}")
        return

    parser = FileParser()
    try:
        args = parser.get_parts_from_args()
    except ArgumentTypeError as e:
        logging.critical(f"Failed to parse arguments: {e}")
        return

    if isinstance(args, bool) and args:
        Renamey.perform_undo()
        return

    try:
        ignore_set = parser.build_ignore_set(resource_path("ignore_list.json"))
    except (OSError, ValueError, AttributeError, TypeError) as e:
        logging.warning(f"Could not load ignore list: {e}. Ignoring nothing.")
        ignore_set = set()

    renamey = Renamey(args, ignore_set)
    renamey.run()


if __name__ == '__main__':
    main()
