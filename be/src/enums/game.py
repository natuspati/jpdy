from enum import StrEnum, auto


class GamePhaseEnum(StrEnum):
    WAITING_FOR_PLAYERS = auto()
    HOST_SELECTING_STARTING_PLAYER = auto()
    PLAYER_SELECTING_PROMPT = auto()
    PLAYER_ANSWERING = auto()
    HOST_JUDGING_ANSWER = auto()
    BUZZ_OPEN = auto()
    FINISHED = auto()


class PlayerConnectionStatusEnum(StrEnum):
    CONNECTED = auto()
    DISCONNECTED = auto()
