import re
import ollama
from pathlib import Path

from models import FileType
from errors import ModelReturnedProse

from .prompt import PromptHelper
from .embed import EmbedHelper


class Generator:
    DATE_COMPILE = re.compile(r"\s*\((?:19|20)\d{2}(?:-(?:19|20)\d{2})?\)\s*$")

    def __init__(self, naming_reference: Path, title_model, episode_model, cache_path: Path | None = None):
        self.title_model = title_model
        self.episode_model = episode_model
        self.title_name = ""
        self.embedder = EmbedHelper(naming_reference, cache_path)

    def get_new_name(self, filename: str, filetype: FileType) -> str:
        matches = self.embedder.get_useful_references(filename, filetype)

        context = ""
        for idx, match in enumerate(matches):
            context += f"Example {idx + 1}:\n- Messy Name: {match['messy']}\n- Target Cleaned Name: {match['clean']}\n\n"

        model_name = self.title_model if filetype in (FileType.TITLE, FileType.MOVIE) else self.episode_model
        response = ollama.chat(model=model_name,
                               messages=[
                                   {"role": "system", "content": PromptHelper.build_system_prompt(context, filetype)},
                                   {"role": "user",
                                    "content": PromptHelper.build_prompt(filename, filetype, self.title_name)}],
                               options={"temperature": 0.0},
                               stream=False)
        new_name = response["message"]["content"].strip()
        if "\n" in new_name:
            raise ModelReturnedProse(f"model returned prose instead of a filename: {new_name!r}")
        if filetype in (FileType.TITLE, FileType.MOVIE):
            self.title_name = self.DATE_COMPILE.sub("", new_name).strip()
        return new_name
