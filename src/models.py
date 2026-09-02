from enum import StrEnum


class ContentType(StrEnum):
    SHOW = "show"
    MOVIE = "movie"


class FileType(StrEnum):
    TITLE = "title"
    SEASON = "season"
    EPISODE = "episode"


class Prompts(StrEnum):
    EXTENSION = "\nThe extension is the final '.' plus letters at the very end of the input name. Copy it verbatim to the end of the output if and only if it is present in the input. If the input has no extension, the output MUST NOT end in a '.' followed by letters. NEVER invent, change, or guess an extension. Any extension shown in the examples that is not in the input is irrelevant."
    EPISODE = "\nOutput the title name followed by the episode number formatted as 'E' + two digits (E01, E07, E43, E710 for three-plus digit numbers). If the input contains no title name, output only the episode token, e.g. 'Ep9.mkv' -> 'E09.mkv', 'Episode 10' -> 'E10'. Never spell out the word 'Episode' or 'Season' in the output. Discard season numbers, 'Part'/'Batch' markers, release groups, resolutions, codecs, hashes, and date indicators."
    SEASON = "\nOutput exactly 'Season NN' where NN is the two-digit season number. Ignore and discard any 'Part' / 'Batch' markers, show titles, release groups, and extensions."
    TITLE = (
        "\nTitles should use the cleaned Title Case title name and are NOT an episode or season. They must NOT include any season indicators."
        "\nIf a title name has an existing date indicator, the title name MUST include it in parenthesis. Make sure to verify if a date indicator is, in fact, a date indicator and not something else with similar formatting. For example, (720p) and (1080p) are resolution formats, but (1995) and (2020) are dates. If a title has multiple dates in a range, such as (2020-2026), include only the earliest date. NEVER invent or guess a date. Any dates shown in the examples that are not in the input are irrelevant."
    )
    CRITICAL = "\nCRITICAL INSTRUCTION: Output ONLY the raw, finalized string of the new filename. Do not provide code blocks, explanations, quotes, notes, or conversational filler."


class ManifestStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"


class ManifestOperation(StrEnum):
    MOVE = "move"
    MKDIR = "mkdir"
