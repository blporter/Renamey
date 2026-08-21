import csv
import re
from pathlib import Path

import ollama
import numpy as np


class Generator:
    LLAMA_MODEL = "llama3.1:8b"
    GEMMA_MODEL = "gemma4:e4b-mlx"
    EMBED_MODEL = "nomic-embed-text"

    SEASON_COMPILE = re.compile(r"^Season \d+$", re.IGNORECASE)
    EPISODE_COMPILE = re.compile(r"\bE\d{2,}\b", re.IGNORECASE)

    title_name = ""

    def __init__(self, csv_path: Path):
        self.examples = self.load_reference(csv_path)

    @staticmethod
    def classify(clean_name: str) -> str:
        name = clean_name.strip()
        if Generator.SEASON_COMPILE.match(name):
            return "season"
        if Generator.EPISODE_COMPILE.search(name):
            return "episode"
        return "title"

    def load_reference(self, csv_path: Path) -> list:
        examples = []
        with open(csv_path, mode='r', encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file, delimiter='\t')
            for row in reader:
                response = ollama.embeddings(model=self.EMBED_MODEL,
                                             prompt=f"search_document: {row['messy_name'].lower()}")
                examples.append({
                    "messy": row['messy_name'],
                    "clean": row['clean_name'],
                    "type": self.classify(row['clean_name']),
                    "vector": response['embedding']
                })
        return examples

    @staticmethod
    def cosine_similarity(v1, v2):
        return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

    def get_useful_references(self, filename: str, filetype: str) -> list:
        target_res = ollama.embeddings(model=self.EMBED_MODEL, prompt=f"search_query: {filename.lower()}")
        target_vector = target_res['embedding']

        candidates = [e for e in self.examples if e['type'] == filetype] or self.examples

        scores = []
        for example in candidates:
            similarity = self.cosine_similarity(target_vector, example['vector'])
            scores.append((similarity, example))

        scores.sort(key=lambda x: x[0], reverse=True)
        limit = 2 if filetype == "season" else 4
        return [item[1] for item in scores[:limit]]

    @staticmethod
    def build_system_prompt(context: str, filetype: str):
        prompt = (
            f"""
            You are an expert file organization system. Your sole job is to rewrite messy, disorganized media filenames into perfectly structured, standardized versions.
            
            Use the following patterns and examples as a direct reference for your formatting decisions:
            {context}
            """
        )
        if filetype != "season":
            prompt += "\nThe extension is the final '.' plus letters at the very end of the input name. Copy it verbatim to the end of the output if and only if it is present in the input. If the input has no extension, the output MUST NOT end in a '.' followed by letters. NEVER invent, change, or guess an extension. Any extension shown in the examples that is not in the input is irrelevant."
        if filetype == "episode":
            prompt += "\nOutput the title name followed by the episode number formatted as 'E' + two digits (E01, E07, E43, E710 for three-plus digit numbers). If the input contains no title name, output only the episode token, e.g. 'Ep9.mkv' -> 'E09.mkv', 'Episode 10' -> 'E10'. Never spell out the word 'Episode' or 'Season' in the output. Discard season numbers, 'Part'/'Batch' markers, release groups, resolutions, codecs, hashes, and date indicators."
        if filetype == "season":
            prompt += "\nOutput exactly 'Season NN' where NN is the two-digit season number. Ignore and discard any 'Part' / 'Batch' markers, show titles, release groups, and extensions."
        if filetype == "title":
            prompt += (
                "\nTitles should use the cleaned Title Case title name and are NOT an episode or season. They must NOT include any season indicators."
                "\nIf a title name has an existing date indicator, the title name MUST include it in parenthesis. Make sure to verify if a date indicator is, in fact, a date indicator and not something else with similar formatting. For example, (720p) and (1080p) are resolution formats, but (1995) and (2020) are dates. If a title has multiple dates in a range, such as (2020-2026), include only the earliest date. NEVER invent or guess a date."
            )
        prompt += "CRITICAL INSTRUCTION: Output ONLY the raw, finalized string of the new filename. Do not provide code blocks, explanations, quotes, notes, or conversational filler."
        return prompt

    def build_prompt(self, filename: str, filetype: str) -> str:
        prompt = (
            f"""
            Analyze this file name and generate a short, cleaned name.  
            Name: {filename}          
            """
        )
        if filetype == "episode" and self.title_name.strip():
            prompt += f"\nUse this as the episode's title for the filename: {self.title_name}"
        return prompt

    def get_new_name(self, filename: str, filetype: str) -> str:
        matches = self.get_useful_references(filename, filetype)

        context = ""
        for idx, match in enumerate(matches):
            context += f"Example {idx + 1}:\n- Messy Name: {match['messy']}\n- Target Cleaned Name: {match['clean']}\n\n"

        model_name = self.GEMMA_MODEL if filetype == "title" else self.LLAMA_MODEL
        response = ollama.chat(model=model_name,
                               messages=[{"role": "system", "content": self.build_system_prompt(context, filetype)},
                                         {"role": "user",
                                          "content": self.build_prompt(filename, filetype)}],
                               options={"temperature": 0.0},
                               stream=False)

        return response["message"]["content"].strip()
