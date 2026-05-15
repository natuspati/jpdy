from enum import StrEnum, auto


class LobbyStateEnum(StrEnum):
    CREATED = auto()
    WAITING_START = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
