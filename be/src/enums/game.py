from enum import StrEnum, auto


class GamePhaseEnum(StrEnum):
    WAITING_FOR_PLAYERS = auto()
    HOST_SELECTING_STARTING_PLAYER = auto()
    PLAYER_SELECTING_PROMPT = auto()
    PLAYER_ANSWERING = auto()
    BUZZ_OPEN = auto()
    ANSWER_REVEAL = auto()
    FINISHED = auto()


class GameResolutionEnum(StrEnum):
    CORRECT = auto()
    UNANSWERED = auto()
    EXPIRED = auto()


class PlayerConnectionStatusEnum(StrEnum):
    CONNECTED = auto()
    DISCONNECTED = auto()
