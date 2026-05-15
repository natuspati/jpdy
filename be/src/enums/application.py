from enum import StrEnum, auto


class AppEnvironmentEnum(StrEnum):
    LOCAL = auto()
    TEST = auto()
    PROD = auto()
