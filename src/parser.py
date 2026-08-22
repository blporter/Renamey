import argparse
import json
import os

from pathlib import Path

import logging


class FileParser:
    @staticmethod
    def build_ignore_set() -> set:
        ignore_path = Path.cwd() / "ignore_list.json"
        with open(ignore_path, "r") as file:
            config = json.load(file)
            return set(config.get("ignore_files", []))

    def get_parts_from_args(self) -> tuple[Path, str, str]:
        parser = argparse.ArgumentParser(
            description="Process a folder or file's absolute filepath and smart-rename via AI models.")
        parser.add_argument('-f', '--filepath', type=str,
                            help="Absolute filepath to a folder", required=True)
        parser.add_argument('-v', '--verbose', action="count", default=0,
                            help="Increase output verbosity (-v or -vv)", required=False)
        parser.add_argument('-t', '--title-model', type=str,
                            help="Name of model for title parsing (default=gemma4:e4b-mlx)", required=False)
        parser.add_argument('-e', '--episode-model', type=str,
                            help="Name of model for season/episode parsing (default=llama3.1:8b)", required=False)
        return self.handle_valid_args(parser.parse_args())

    @staticmethod
    def handle_valid_args(args) -> tuple[Path, str, str]:
        logger = logging.getLogger()
        if args.verbose >= 2:
            logger.setLevel(level=logging.DEBUG)
        elif args.verbose == 1:
            logger.setLevel(level=logging.INFO)

        filepath = Path(os.path.expandvars(args.filepath)).expanduser()
        if not filepath.is_absolute():
            logging.debug(f"{filepath} is relative, resolving to {Path.cwd() / Path(filepath)}")
            filepath = Path.cwd() / Path(filepath)
        if not filepath.exists():
            raise argparse.ArgumentTypeError(f"{args.filepath} does not exist.")

        title_model = args.title_model if args.title_model else "gemma4:e4b-mlx"
        episode_model = args.episode_model if args.episode_model else "llama3.1:8b"

        logging.info(
            f"Proceeding with filepath: {filepath}, title model: {title_model}, episode model: {episode_model}")
        return filepath, title_model, episode_model
