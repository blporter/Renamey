# Renamey

Use local AI models to bulk rename junk files into clean snake_case.

### Setup

Use `make run FILEPATH="/Absolute/Path/To/Junk/Name"` to run from source, or `make build` using `pyinstaller` to build a
Unix Executable.

It can then be run as a script via `./main -f "/Absolute/Path/To/Junk/Name"`.

### Overview

The `main.py` script handles argument parsing and file traversing for nested folder structures, while `generator.py`
handles the AI workflow and context references.

The models used are `gemma4:e4b-mlx` for title name generation, `llama3.1:8b` for season and episode name parsing, and
`nomic-embed-text` for RAG references and context.

The data source for RAG is the local database `naming_reference.csv`, which contains a collection of "messy" file names
and their expected "clean" counterparts.

A "messy" show with nested season folders will go from this:
<pre>
├── [RUBaDUB] Kaiju No. 8 (S1 Complete) (1080p) (Dual Audio) 
    ├── Kaiju No. 8 S1
        ├── [RUBaDUB][1080p] Kaiju No. 8 - 01 [BD x265 10bit Dual Audio AC3][3012EC12].mkv
        ├── [RUBaDUB][1080p] Kaiju No. 8 - 02 [BD x265 10bit Dual Audio AC3][3012EC12].mkv
        └── [RUBaDUB][1080p] Kaiju No. 8 - 03 [BD x265 10bit Dual Audio AC3][3012EC12].mkv
</pre>
to this:
<pre>
├── kaiju_no_8
    ├── season_01
        ├── episode_01.mkv
        ├── episode_02.mkv
        └── episode_03.mkv
</pre>

I have found that this naming convention makes automated file detection more predictable for media servers.