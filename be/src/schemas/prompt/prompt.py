from pydantic import Field, computed_field, field_validator, model_validator

from configs.constants import NUM_PROMPTS_IN_CATEGORY
from enums import AnswerTypeEnum, QuestionTypeEnum
from schemas.base import BaseSchema, OneFieldSetSchemaMixin
from schemas.media import MediaAssetInDBSchema, MediaReferenceSchema


class QuestionContentSchema(BaseSchema):
    type: QuestionTypeEnum
    text: str
    media: MediaReferenceSchema | None = None


class AnswerContentSchema(BaseSchema):
    type: AnswerTypeEnum
    text: str
    media: MediaReferenceSchema | None = None


class PromptInDBSchema(BaseSchema):
    id: int
    question: str
    question_type: QuestionTypeEnum
    answer: str
    answer_type: AnswerTypeEnum
    question_media_asset_id: int | None
    answer_media_asset_id: int | None
    category_id: int
    order: int | None
    question_media_asset: MediaAssetInDBSchema | None = Field(default=None, exclude=True)
    answer_media_asset: MediaAssetInDBSchema | None = Field(default=None, exclude=True)

    @computed_field
    @property
    def question_content(self) -> QuestionContentSchema:
        return QuestionContentSchema(
            type=self.question_type,
            text=self.question,
            media=(
                MediaReferenceSchema.from_asset(self.question_media_asset)
                if self.question_media_asset is not None
                else None
            ),
        )

    @computed_field
    @property
    def answer_content(self) -> AnswerContentSchema:
        return AnswerContentSchema(
            type=self.answer_type,
            text=self.answer,
            media=(
                MediaReferenceSchema.from_asset(self.answer_media_asset)
                if self.answer_media_asset is not None
                else None
            ),
        )


class PromptCreateSchema(BaseSchema):
    question: str = Field(min_length=1, max_length=256)
    question_type: QuestionTypeEnum
    answer: str = Field(min_length=1, max_length=256)
    answer_type: AnswerTypeEnum
    question_media_asset_id: int | None = None
    answer_media_asset_id: int | None = None
    order: int = Field(ge=1, le=NUM_PROMPTS_IN_CATEGORY)

    @model_validator(mode="after")
    def _validate_media_assignments(self) -> PromptCreateSchema:
        _validate_media_assignment(
            content_type=self.question_type,
            asset_id=self.question_media_asset_id,
            field_name="question_media_asset_id",
        )
        _validate_media_assignment(
            content_type=self.answer_type,
            asset_id=self.answer_media_asset_id,
            field_name="answer_media_asset_id",
        )
        return self


class PromptUpdateSchema(OneFieldSetSchemaMixin):
    question: str | None = Field(default=None, min_length=1, max_length=256)
    question_type: QuestionTypeEnum | None = None
    answer: str | None = Field(default=None, min_length=1, max_length=256)
    answer_type: AnswerTypeEnum | None = None
    question_media_asset_id: int | None = None
    answer_media_asset_id: int | None = None

    @field_validator(
        "question",
        "question_type",
        "answer",
        "answer_type",
        mode="before",
    )
    @classmethod
    def _reject_explicit_null(cls, v: object) -> object:
        if v is None:
            raise ValueError("must not be null")
        return v

    @model_validator(mode="after")
    def _validate_partial_media_assignments(self) -> PromptUpdateSchema:
        has_question_type = "question_type" in self.model_fields_set
        has_question_media = "question_media_asset_id" in self.model_fields_set
        if has_question_type and has_question_media:
            _validate_media_assignment(
                content_type=self.question_type,
                asset_id=self.question_media_asset_id,
                field_name="question_media_asset_id",
            )
        has_answer_type = "answer_type" in self.model_fields_set
        has_answer_media = "answer_media_asset_id" in self.model_fields_set
        if has_answer_type and has_answer_media:
            _validate_media_assignment(
                content_type=self.answer_type,
                asset_id=self.answer_media_asset_id,
                field_name="answer_media_asset_id",
            )
        return self


def _validate_media_assignment(
    content_type: QuestionTypeEnum | AnswerTypeEnum,
    asset_id: int | None,
    field_name: str,
) -> None:
    if content_type == QuestionTypeEnum.TEXT:
        if asset_id is not None:
            raise ValueError(f"{field_name} must be empty for text content")
        return
    if asset_id is None:
        raise ValueError(f"{field_name} is required for media content")
