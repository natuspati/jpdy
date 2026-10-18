from enum import StrEnum, auto


class PromptCategoryKindEnum(StrEnum):
    STANDARD = auto()
    FINAL = auto()


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
