# Renamey

Use local AI models to bulk rename junk files into clean Title Case.

### Setup

Use `make run FILEPATH="/Absolute/Path/To/Junk/Name"` to run from source, or `make build` using `pyinstaller` to build a
Unix Executable.

It can then be run as a script via `./renamey -f "/Absolute/Path/To/Junk/Name"`.

### Overview

The `renamey.py` script handles argument parsing and file traversing for nested folder structures, while `generator.py`
handles the AI workflow and context references.

The models used are `gemma4:e4b-mlx` for title name generation, `llama3.1:8b` for season and episode name parsing, and
`nomic-embed-text` for RAG references and context.

The data source for RAG is the local database `naming_reference.csv`, which contains a collection of "messy" file names
and their expected "clean" counterparts.

A "messy" show with nested season folders will go from this:
<pre>
├── [RUBaDUB] Kaiju No. 8 (S1 Complete) (2022) (1080p) (Dual Audio) 
    ├── Kaiju No. 8 S1
        ├── [RUBaDUB][1080p] Kaiju No. 8 - 01 [BD x265 10bit Dual Audio AC3][3012EC12].mkv
        ├── [RUBaDUB][1080p] Kaiju No. 8 - 02 [BD x265 10bit Dual Audio AC3][3012EC12].mkv
        └── [RUBaDUB][1080p] Kaiju No. 8 - 03 [BD x265 10bit Dual Audio AC3][3012EC12].mkv
</pre>
to this:
<pre>
├── Kaiju No. 8 (2022)
    ├── Season 01
        ├── Kaiju No. 8 E01.mkv
        ├── Kaiju No. 8 E02.mkv
        └── Kaiju No. 8 E03.mkv
</pre>

This is the supported naming convention listed by Jellyfin in their docs: <https://jellyfin.org/docs/general/server/media/shows/>

### TODO
- [ ] Add an optional `verbosity` flag.
- [ ] Add an optional `dry-run` flag with planned execution output.