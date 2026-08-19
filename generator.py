import csv

import ollama
import numpy as np


class Generator:
    LLAMA_MODEL = "llama3.1:8b"
    GEMMA_MODEL = "gemma4:e4b-mlx"
    EMBED_MODEL = "nomic-embed-text"

    def __init__(self, csv_file: str = "naming_reference.csv"):
        self.examples = self.load_reference(csv_file)

    def load_reference(self, csv_file: str) -> list:
        examples = []
        with open(csv_file, mode='r', encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file, delimiter='\t')
            next(reader)
            for row in reader:
                text_to_embed = f"Messy: {row['messy_name']}"
                response = ollama.embeddings(model=self.EMBED_MODEL, prompt=text_to_embed)
                examples.append({
                    "messy": row['messy_name'],
                    "clean": row['clean_name'],
                    "vector": response['embedding']
                })
        return examples

    @staticmethod
    def cosine_similarity(v1, v2):
        return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

    def get_useful_references(self, filename: str, filetype: str) -> list:
        target_res = ollama.embeddings(model=self.EMBED_MODEL, prompt=f"Messy: {filename}")
        target_vector = target_res['embedding']

        scores = []
        for example in self.examples:
            similarity = self.cosine_similarity(target_vector, example['vector'])
            scores.append((similarity, example))

        scores.sort(key=lambda x: x[0], reverse=True)
        if filetype == "title":
            return [item[1] for item in scores[:4]]
        return [item[1] for item in scores[:2]]

    @staticmethod
    def build_system_prompt(context):
        return (
            f"""
            You are an expert file organization system. Your sole job is to rewrite messy, disorganized media filenames into perfectly structured, standardized versions.
            
            Use the following patterns and examples as a direct reference for your formatting decisions:
            {context}
            
            Episodes take highest priority, followed by seasons, followed by the title name itself. If a file indicates that it is an episode, the new name must not include a season or title. If a file indicates that it is *not* an episode, but *is* a season, the new name must not include the title.
            
            If a file has an existing extension, you MUST keep the extension in the new file name. If it does not have an existing extension, do NOT add one.
            
            CRITICAL INSTRUCTION: Output ONLY the raw, finalized string of the new filename. Do not provide code blocks, explanations, quotes, notes, or conversational filler.
            """
        )

    @staticmethod
    def build_prompt(filename, filetype):
        return (
            f"""
            Analyze this file name and generate a short, cleaned name in snake_case.
            
            This file is a(n) {filetype} and should be renamed accordingly:
            Episodes MUST be only "episode_" followed by the episode number, with no other title, prefix, or suffix besides the number. Every episode MUST have a file extension.
            Seasons MUST be only "season_" followed by the season number, with no other title, prefix, or suffix besides the number.
            Titles should use the cleaned snake_case title name and are NOT an episode or season.
            
            Name: {filename}
            """
        )

    def get_new_name(self, filename: str, filetype: str) -> str:
        matches = self.get_useful_references(filename, filetype)

        context = ""
        for idx, match in enumerate(matches):
            context += f"Example {idx + 1}:\n- Messy Name: {match['messy']}\n- Target Cleaned Name: {match['clean']}\n\n"

        model_name = self.GEMMA_MODEL if filetype == "title" else self.LLAMA_MODEL
        response = ollama.chat(model=model_name,
                               messages=[{"role": "system", "content": self.build_system_prompt(context)},
                                         {"role": "user", "content": self.build_prompt(filename, filetype)}],
                               options={"temperature": 0.0},
                               stream=False)

        return response["message"]["content"].strip()
