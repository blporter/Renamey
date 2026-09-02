import argparse
import json
import os

from pathlib import Path

import logging

from models import ContentType


class FileParser:
    @staticmethod
    def build_ignore_set(ignore_path: Path) -> set:
        with open(ignore_path, "r", encoding="utf-8") as file:
            config = json.load(file)
        ignored_files = set(config.get("ignore_files", []))
        logging.debug(f"Files to be ignored: {ignored_files}")
        return ignored_files

    def get_parts_from_args(self) -> tuple[ContentType, Path, str, str, bool] | bool:
        parser = argparse.ArgumentParser(
            description="Process a folder or file's absolute filepath and smart-rename via AI models.")
        subparsers = parser.add_subparsers(dest="subcommand", help="Available sub-commands", required=True)

        rename_parser = subparsers.add_parser("rename", help="Rename a file, or all nested files and folders")
        required_group = rename_parser.add_argument_group("Required arguments")
        required_group.add_argument('-c', '--content-type', type=str,
                                    help="Content type for parsing (show or movie)", required=True)
        required_group.add_argument('-f', '--filepath', type=str,
                                    help="Absolute filepath to a folder", required=True)
        optional_group = rename_parser.add_argument_group("Optional arguments")
        optional_group.add_argument('--dry-run', action="store_true",
                                    help="Print changes without renaming", required=False)
        optional_group.add_argument('-e', '--episode-model', type=str,
                                    help="Name of model for episode parsing (default=llama3.1:8b)", required=False)
        optional_group.add_argument('-t', '--title-model', type=str,
                                    help="Name of model for title parsing (default=gemma4:e4b-mlx)", required=False)
        optional_group.add_argument('-v', '--verbose', action="count", default=0,
                                    help="Increase output verbosity (-v or -vv)", required=False)

        subparsers.add_parser("undo", help="Undo the last rename operation")

        args = parser.parse_args()
        print(args)
        if args.subcommand == "undo":
            return True
        else:
            return self.handle_valid_args(args)

    @staticmethod
    def handle_valid_args(args) -> tuple[ContentType, Path, str, str, bool]:
        logger = logging.getLogger()
        if args.verbose >= 2:
            logger.setLevel(level=logging.DEBUG)
        elif args.verbose == 1:
            logger.setLevel(level=logging.INFO)
        logging.debug(f"Args from parser: {args}")

        content_arg = args.content_type.lower().strip()
        if content_arg not in ("movie", "show"):
            raise argparse.ArgumentTypeError(f"content type must be either 'movie' or 'show', got {content_arg}")
        content_type = ContentType(content_arg)

        filepath = Path(os.path.expandvars(args.filepath)).expanduser()
        if not filepath.is_absolute():
            logging.debug(f"{filepath} is relative, resolving to {Path.cwd() / Path(filepath)}")
            filepath = Path.cwd() / Path(filepath)
        if not filepath.exists():
            raise argparse.ArgumentTypeError(f"{args.filepath} does not exist.")

        title_model = args.title_model if args.title_model else "gemma4:e4b-mlx"
        episode_model = args.episode_model if args.episode_model else "llama3.1:8b"

        logging.info(
            f"Proceeding with content type: {content_type.value}, filepath: {filepath}, title model: {title_model}, episode model: {episode_model}, dry run: {args.dry_run}")
        return content_type, filepath, title_model, episode_model, args.dry_run
