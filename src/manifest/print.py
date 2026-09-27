from pathlib import Path

from tqdm import tqdm

from models import FileType, ManifestOperation

DEPTH_MAP = {
    FileType.TITLE.value: 0,
    FileType.SEASON.value: 1,
    FileType.EPISODE.value: 2,
    FileType.MOVIE.value: 1
}


def pretty_print(manifest: dict, reverse: bool = False):
    operations = manifest["operations"]
    created_dirs = set()
    for op in operations:
        if op["op_type"] == ManifestOperation.MKDIR.value:
            created_dirs.add(op["path"])

    skip_indices = find_skip_indices(operations, created_dirs)
    moves = [op for i, op in enumerate(operations)
             if i not in skip_indices
             and op["op_type"] == ManifestOperation.MOVE.value
             and Path(op["from"]).name != Path(op["to"]).name]

    entries = []
    for op in moves:
        filetype = op["filetype"]
        from_name = Path(op["from"]).name
        to_name = Path(op["to"]).name
        if reverse:
            from_name, to_name = to_name, from_name

        entries.append({"depth": DEPTH_MAP[filetype],
                        "filetype": filetype,
                        "from": from_name,
                        "to": to_name})
    update_last_entry(entries)
    update_parent_continuation(entries)
    handle_print(entries)


def find_skip_indices(operations: list, created_dirs: set) -> set:
    skip_indices = set()
    for i, op in enumerate(operations):
        if op["op_type"] == ManifestOperation.MKDIR.value:
            skip_indices.add(i)
        elif op["op_type"] == ManifestOperation.MOVE.value:
            to_parent = str(Path(op["to"]).parent)
            from_parent = str(Path(op["from"]).parent)
            if to_parent in created_dirs and from_parent != to_parent:
                skip_indices.add(i)
    return skip_indices


def update_last_entry(entries: list):
    for i, entry in enumerate(entries):
        depth = entry["depth"]
        is_last = True
        for future in entries[i + 1:]:
            if future["depth"] == depth:
                is_last = False
                break
            if future["depth"] < depth:
                break
        entry["is_last"] = is_last


def update_parent_continuation(entries: list):
    for i, entry in enumerate(entries):
        if entry["depth"] == 2:
            entry["parent_continues"] = any(e["depth"] == 1 for e in entries[i + 1:])
        else:
            entry["parent_continues"] = False


def handle_print(entries: list):
    for entry in entries:
        label = entry["filetype"].capitalize()
        output = f"{label}: {entry['from']} --> {entry['to']}"

        if entry["depth"] == 0:
            tqdm.write(output)
        elif entry["depth"] == 1:
            icon = "└" if entry["is_last"] else "├"
            tqdm.write(f"\t{icon}── {output}")
        elif entry["depth"] == 2:
            icon = "└" if entry["is_last"] else "├"
            vert = "│" if entry["parent_continues"] else " "
            tqdm.write(f"\t{vert}\t{icon}── {output}")
