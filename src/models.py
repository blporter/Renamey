from enum import StrEnum


class ContentType(StrEnum):
    SHOW = "show"
    MOVIE = "movie"


class FileType(StrEnum):
    TITLE = "title"
    SEASON = "season"
    EPISODE = "episode"
