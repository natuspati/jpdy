from enum import StrEnum, auto


class HealthStatusEnum(StrEnum):
    OK = auto()
    DEGRADED = auto()
    DOWN = auto()
