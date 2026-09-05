# Renamey

Use local AI models to bulk rename media files with junk names into clean Title Case. The intended use for this program is to automate renaming into the folder structure expected by a Jellyfin media server.

### Setup

Use `make run CONTENT=movie FILEPATH="/Absolute/Path/To/Junk/Name"` to run from source, or `make build` using `pyinstaller` to build a Unix Executable.

It can then be run as a script via:
```bash
./renamey rename -c show -f "/Absolute/Path/To/Junk/Name"
```

Content type (movie or show) and filepath are required. Optional parameters include models, verbosity, and dry run.
Ex:
```bash
./renamey rename --content-type show --filepath "/Absolute/Path/To/Junk/Name" --title-model "gemma4:e4b-mlx" --episode-model "llama3.1:8b" -v --dry-run
```

### Overview

The `main.py` script handles traversing for nested folder structures, `parser.py` handles argument parsing and validation, and `generator.py` handles the AI workflow and context references.

The default models used are `gemma4:e4b-mlx` for title name generation and `llama3.1:8b` for episode name parsing. For RAG references and context, we use `nomic-embed-text`.

The data source for RAG is the local database `naming_reference.csv`, which contains a collection of "messy" file names and their expected "clean" counterparts.

A "messy" show with nested season folders will go from this:
<pre>
[RUBaDUB] Kaiju No. 8 (2022) (1080p) (Dual Audio) 
    ├── Kaiju No. 8 S1
    │   ├── [RUBaDUB][1080p] Kaiju No. 8 - 01 [BD x265 10bit Dual Audio AC3][3012EC12].mkv
    │   ├── [RUBaDUB][1080p] Kaiju No. 8 - 02 [BD x265 10bit Dual Audio AC3][3012EC12].mkv
    │   ├── [RUBaDUB][1080p] Kaiju No. 8 - 03 [BD x265 10bit Dual Audio AC3][3012EC12].mkv
</pre>
to this:
<pre>
Kaiju No. 8 (2022)
    ├── Season 01
    │   ├── Kaiju No. 8 E01.mkv
    │   ├── Kaiju No. 8 E02.mkv
    │   ├── Kaiju No. 8 E03.mkv
</pre>

This is the supported naming convention listed by Jellyfin in their docs: <https://jellyfin.org/docs/general/server/media/shows/>
