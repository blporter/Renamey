# Renamey
Use local AI models to bulk rename junk files into clean snake_case.

### Setup

Use `make run FILEPATH="/Absolute/Path/To/Junk/Name"` to run from source, or `make build` using `pyinstaller` to build a Unix Executable.

It can then be run as a script via `./main -f "/Absolute/Path/To/Junk/Name"`.

### Overview

The `main.py` script handles argument parsing and file traversing for nested folder structures, while `generator.py` handles the AI workflow and context references.

The models used are `gemma4:e4b-mlx` for title name generation, `llama3.1:8b` for season and episode name parsing, and `nomic-embed-text` for RAG references and context.

The data source for RAG is the local database `naming_reference.csv`, which contains a collection of "messy" file names and their expected "clean" counterparts.