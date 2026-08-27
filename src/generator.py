import csv
import logging
import re
from pathlib import Path
from numpy import dot, linalg

import ollama

from models import FileType


class Generator:
    EMBED_MODEL = "nomic-embed-text"

    SEASON_COMPILE = re.compile(r"^Season \d+$", re.IGNORECASE)
    EPISODE_COMPILE = re.compile(r"\bE\d{2,}\b", re.IGNORECASE)
    DATE_COMPILE = re.compile(r"\s*\((?:19|20)\d{2}(?:-(?:19|20)\d{2})?\)\s*$")

    title_name = ""

    def __init__(self, csv_path: Path, title_model: str, episode_model: str):
        self.TITLE_MODEL = title_model
        self.EPISODE_MODEL = episode_model
        self.examples = self.load_reference(csv_path)

    @staticmethod
    def classify(clean_name: str) -> FileType:
        name = clean_name.strip()
        if Generator.SEASON_COMPILE.match(name):
            return FileType.SEASON
        if Generator.EPISODE_COMPILE.search(name):
            return FileType.EPISODE
        return FileType.TITLE

    def load_reference(self, csv_path: Path) -> list:
        logging.info(f"Loading from reference file {csv_path}")
        examples = []
        with open(csv_path, mode='r', encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file, delimiter='\t')
            for row in reader:
                response = ollama.embeddings(model=self.EMBED_MODEL,
                                             prompt=f"search_document: {row['messy_name'].lower()}")
                examples.append({
                    "messy": row['messy_name'],
                    "clean": row['clean_name'],
                    "type": self.classify(row['clean_name']).value,
                    "vector": response['embedding']
                })
        return examples

    @staticmethod
    def cosine_similarity(v1, v2):
        return dot(v1, v2) / (linalg.norm(v1) * linalg.norm(v2))

    def get_useful_references(self, filename: str, filetype: FileType) -> list:
        target_res = ollama.embeddings(model=self.EMBED_MODEL, prompt=f"search_query: {filename.lower()}")
        target_vector = target_res['embedding']

        candidates = [e for e in self.examples if e['type'] == filetype.value] or self.examples

        scores = []
        for example in candidates:
            similarity = self.cosine_similarity(target_vector, example['vector'])
            scores.append((similarity, example))

        scores.sort(key=lambda x: x[0], reverse=True)
        limit = 2 if filetype == FileType.SEASON else 4
        got_references = {}
        for score in scores[:limit]:
            got_references[score[0]] = {"messy": score[1]["messy"],
                                        "clean": score[1]["clean"],
                                        "type": score[1]["type"]}
        logging.debug(f"For filename {filename}, got references {got_references}")
        return [item[1] for item in scores[:limit]]

    @staticmethod
    def build_system_prompt(context: str, filetype: FileType):
        prompt = (
            f"""
You are an expert file organization system. Your sole job is to rewrite messy, disorganized media filenames into perfectly structured, standardized versions.

Use the following patterns and examples as a direct reference for your formatting decisions:
{context}
"""
        )
        if filetype != FileType.SEASON:
            prompt += "\nThe extension is the final '.' plus letters at the very end of the input name. Copy it verbatim to the end of the output if and only if it is present in the input. If the input has no extension, the output MUST NOT end in a '.' followed by letters. NEVER invent, change, or guess an extension. Any extension shown in the examples that is not in the input is irrelevant."
        if filetype == FileType.EPISODE:
            prompt += "\nOutput the title name followed by the episode number formatted as 'E' + two digits (E01, E07, E43, E710 for three-plus digit numbers). If the input contains no title name, output only the episode token, e.g. 'Ep9.mkv' -> 'E09.mkv', 'Episode 10' -> 'E10'. Never spell out the word 'Episode' or 'Season' in the output. Discard season numbers, 'Part'/'Batch' markers, release groups, resolutions, codecs, hashes, and date indicators."
        if filetype == FileType.SEASON:
            prompt += "\nOutput exactly 'Season NN' where NN is the two-digit season number. Ignore and discard any 'Part' / 'Batch' markers, show titles, release groups, and extensions."
        if filetype == FileType.TITLE:
            prompt += (
                "\nTitles should use the cleaned Title Case title name and are NOT an episode or season. They must NOT include any season indicators."
                "\nIf a title name has an existing date indicator, the title name MUST include it in parenthesis. Make sure to verify if a date indicator is, in fact, a date indicator and not something else with similar formatting. For example, (720p) and (1080p) are resolution formats, but (1995) and (2020) are dates. If a title has multiple dates in a range, such as (2020-2026), include only the earliest date. NEVER invent or guess a date. Any dates shown in the examples that are not in the input are irrelevant."
            )
        prompt += "\nCRITICAL INSTRUCTION: Output ONLY the raw, finalized string of the new filename. Do not provide code blocks, explanations, quotes, notes, or conversational filler."
        return prompt

    def build_prompt(self, filename: str, filetype: FileType) -> str:
        prompt = (
            f"""
Analyze this file name and generate a short, cleaned name.  
Name: {filename}          
"""
        )
        if filetype == FileType.EPISODE and self.title_name.strip():
            prompt += f"\nThe output MUST start with this exact string, character for character: {self.title_name}"
            prompt += "\nDo NOT re-capitalize, re-case, translate, reorder, or otherwise alter it. Append the episode token (and the extension, if any) after it, even if the input name is already correctly formatted."
        return prompt

    def get_new_name(self, filename: str, filetype: FileType) -> str:
        matches = self.get_useful_references(filename, filetype)

        context = ""
        for idx, match in enumerate(matches):
            context += f"Example {idx + 1}:\n- Messy Name: {match['messy']}\n- Target Cleaned Name: {match['clean']}\n\n"

        model_name = self.TITLE_MODEL if filetype == FileType.TITLE else self.EPISODE_MODEL
        response = ollama.chat(model=model_name,
                               messages=[{"role": "system", "content": self.build_system_prompt(context, filetype)},
                                         {"role": "user",
                                          "content": self.build_prompt(filename, filetype)}],
                               options={"temperature": 0.0},
                               stream=False)
        new_name = response["message"]["content"].strip()
        if "\n" in new_name:
            raise ValueError(f"model returned prose instead of a filename: {new_name!r}")
        if filetype == FileType.TITLE:
            self.title_name = self.DATE_COMPILE.sub("", new_name).strip()
        return new_name
