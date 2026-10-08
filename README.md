# Renamey

Use local AI models to bulk rename media files with junk names into clean Title Case. The intended use for this program is to automate renaming into the folder structure expected by a Jellyfin media server.

### Install

Install using Homebrew:

```bash
brew tap blporter/utilities
brew install renamey
```

To uninstall:
```bash
brew uninstall renamey
```

#### Setup from source

The Makefile includes environment setup and installation. The `make setup` command can be run by itself, and is also invoked by the other `make` targets.

Use `make run-rename CONTENT=movie FILEPATH="/Absolute/Path/To/Junk/Name"` to run from source, or `make build` to build the bundled project.

It can then be run as a script via:
```bash
./dist/renamey rename -c show -f "/Absolute/Path/To/Junk/Name"
```

**Note**: The first cold-start run can be slow. Subsequent runs should be fast.

### Usage

Content type (movie or show) and filepath are required. Optional parameters include models, verbosity (-v or -vv), resume, and dry run.
```bash
renamey rename --content-type show --filepath "/Absolute/Path/To/Junk/Name" --title-model "gemma4:e4b-mlx" --episode-model "llama3.1:8b" -v --dry-run
```

An interrupted run can be resumed by passing the `--resume` flag. This will skip any files that have already been processed and rerun starting from the last file. It is also compatible with `--dry-run`.
```bash
renamey rename --content-type show --filepath "/Absolute/Path/To/Junk/Name" --resume --dry-run -v
```

Undo the previous rename operation by using the `undo` subcommand instead of `rename`. Undo has no other flags except optional verbosity (-v or -vv).
```bash
renamey undo -v
```

Modify the default models by running `renamey config` and providing the model names. Running `renamey rename` will use the new models by default. Both `title_model` and `episode_model` are optional.
```bash
renamey config --title-model "gemma4:e4b-mlx" --episode-model "llama3.1:8b"
```

### Overview

The `main` script handles traversing for nested folder structures, `parser` handles argument parsing and validation, `manifest` handles logging and file movement, `generator` handles the AI workflow and context references, and finally `undoer` handles undoing an existing manifest.

The default models used are `gemma4:e4b-mlx` for title name generation and `llama3.1:8b` for episode name parsing. For RAG references and context, we use `nomic-embed-text`.

The data source for RAG is the local database `src/assets/naming_reference.csv`, which contains a collection of "messy" file names and their expected "clean" counterparts. The script will compare to the diff of the file on this repo, and pull any new entries. It uses the version bundled in the release if run offline or if unable to check the git diff.

A "messy" show with nested season folders will go from this:
<pre>
[RUBaDUB] Kaiju No. 8 (2022) (1080p) (Dual Audio) 
    └── Kaiju No. 8 S1
        ├── [RUBaDUB][1080p] Kaiju No. 8 - 01 [BD x265 10bit Dual Audio AC3][3012EC12].mkv
        ├── [RUBaDUB][1080p] Kaiju No. 8 - 02 [BD x265 10bit Dual Audio AC3][3012EC12].mkv
        └── [RUBaDUB][1080p] Kaiju No. 8 - 03 [BD x265 10bit Dual Audio AC3][3012EC12].mkv
</pre>
to this:
<pre>
Kaiju No. 8 (2022)
    └── Season 01
        ├── Kaiju No. 8 E01.mkv
        ├── Kaiju No. 8 E02.mkv
        └── Kaiju No. 8 E03.mkv
</pre>

This is the supported naming convention listed by Jellyfin in their docs: <https://jellyfin.org/docs/general/server/media/shows/>
