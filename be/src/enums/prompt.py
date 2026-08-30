from enum import StrEnum, auto


class QuestionTypeEnum(StrEnum):
    TEXT = auto()
    IMAGE = auto()
    AUDIO = auto()
    VIDEO = auto()


class AnswerTypeEnum(StrEnum):
    TEXT = auto()
    IMAGE = auto()
    AUDIO = auto()
    VIDEO = auto()


class MediaKindEnum(StrEnum):
    IMAGE = auto()
    AUDIO = auto()
    VIDEO = auto()
