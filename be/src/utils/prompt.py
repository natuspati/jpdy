from typing import TYPE_CHECKING

from configs.constants import NUM_PROMPTS_IN_CATEGORY
from enums import AnswerTypeEnum, MediaKindEnum, QuestionTypeEnum
from errors.request import BadRequestError, ForbiddenError, NotFoundError
from schemas.prompt.nested import (
    PromptCategoryResponseSchema,
    PromptCategoryWithPromptsInDBSchema,
)
from schemas.prompt.prompt import (
    AnswerContentSchema,
    PromptInDBSchema,
    PromptResponseSchema,
    QuestionContentSchema,
)
from schemas.user.base import UserPublicSchema
from utils.media import build_media_reference, ensure_owned_media_asset

if TYPE_CHECKING:
    from database import UnitOfWork


async def ensure_owned_category(
    uow: UnitOfWork,
    category_id: int,
    user: UserPublicSchema,
    prompt_id: int | None = None,
) -> PromptCategoryWithPromptsInDBSchema:
    category = await uow.prompt_category_repo.select_prompt_category(category_id=category_id)
    if category is None:
        raise NotFoundError(f"Prompt category {category_id} not found")
    if category.owner_id != user.id:
        raise ForbiddenError("Only the owner can modify this prompt category")
    if prompt_id is not None and not any(prompt.id == prompt_id for prompt in category.prompts):
        raise NotFoundError(f"Prompt {prompt_id} not found in category {category_id}")
    return category


def validate_content_media_pair(
    content_type: QuestionTypeEnum | AnswerTypeEnum,
    asset_id: int | None,
    field_name: str,
) -> None:
    if media_kind_for_content_type(content_type) is None and asset_id is not None:
        raise BadRequestError(f"{field_name} must be empty for text content")
    if media_kind_for_content_type(content_type) is not None and asset_id is None:
        raise BadRequestError(f"{field_name} is required for media content")


async def validate_prompt_media(
    *,
    uow: UnitOfWork,
    user: UserPublicSchema,
    question_type: QuestionTypeEnum,
    question_media_asset_id: int | None,
    answer_type: AnswerTypeEnum,
    answer_media_asset_id: int | None,
) -> None:
    validate_content_media_pair(
        question_type,
        question_media_asset_id,
        "question_media_asset_id",
    )
    validate_content_media_pair(
        answer_type,
        answer_media_asset_id,
        "answer_media_asset_id",
    )
    await ensure_owned_media_asset(
        uow=uow,
        asset_id=question_media_asset_id,
        expected_kind=media_kind_for_content_type(question_type),
        user_id=user.id,
        field_name="question_media_asset_id",
    )
    await ensure_owned_media_asset(
        uow=uow,
        asset_id=answer_media_asset_id,
        expected_kind=media_kind_for_content_type(answer_type),
        user_id=user.id,
        field_name="answer_media_asset_id",
    )


def media_kind_for_content_type(
    content_type: QuestionTypeEnum | AnswerTypeEnum,
) -> MediaKindEnum | None:
    if content_type.value == QuestionTypeEnum.TEXT:
        return None
    return MediaKindEnum(content_type.value)


def build_prompt_response(prompt: PromptInDBSchema) -> PromptResponseSchema:
    return PromptResponseSchema(
        **prompt.model_dump(),
        question_content=QuestionContentSchema(
            type=prompt.question_type,
            text=prompt.question,
            media=(
                build_media_reference(prompt.question_media_asset)
                if prompt.question_media_asset is not None
                else None
            ),
        ),
        answer_content=AnswerContentSchema(
            type=prompt.answer_type,
            text=prompt.answer,
            media=(
                build_media_reference(prompt.answer_media_asset)
                if prompt.answer_media_asset is not None
                else None
            ),
        ),
    )


def validate_prompt_order(
    category_id: int,
    prompt_order: dict[int, int],
    category: PromptCategoryWithPromptsInDBSchema,
) -> None:
    if not prompt_order:
        raise BadRequestError("Prompt order mapping must not be empty")
    new_orders = list(prompt_order.values())
    if len(set(new_orders)) != len(new_orders):
        raise BadRequestError("Prompt orders must be unique within the mapping")
    for order_value in new_orders:
        if not 1 <= order_value <= NUM_PROMPTS_IN_CATEGORY:
            raise BadRequestError(
                f"Prompt order must be between 1 and {NUM_PROMPTS_IN_CATEGORY}",
            )
    category_prompt_ids = {prompt.id for prompt in category.prompts}
    missing = set(prompt_order) - category_prompt_ids
    if missing:
        raise BadRequestError(
            f"Prompts {sorted(missing)} do not belong to category {category_id}",
        )


def build_prompt_category_response(
    category: PromptCategoryWithPromptsInDBSchema,
) -> PromptCategoryResponseSchema:
    return PromptCategoryResponseSchema(
        **category.model_dump(exclude={"prompts"}),
        prompts=[build_prompt_response(prompt) for prompt in category.prompts],
    )


def redact_category_prompts(
    category: PromptCategoryWithPromptsInDBSchema,
    viewer_id: int,
) -> PromptCategoryWithPromptsInDBSchema:
    if category.owner_id == viewer_id:
        return category
    return category.model_copy(
        update={
            "prompts": [
                prompt.model_copy(
                    update={
                        "question": "",
                        "question_type": QuestionTypeEnum.TEXT,
                        "question_media_asset_id": None,
                        "question_media_asset": None,
                        "answer": "",
                        "answer_type": AnswerTypeEnum.TEXT,
                        "answer_media_asset_id": None,
                        "answer_media_asset": None,
                    },
                )
                for prompt in category.prompts
            ],
        },
    )
