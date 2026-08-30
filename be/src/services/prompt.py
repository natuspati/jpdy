from typing import Annotated

from fastapi import Depends

from database import UnitOfWork
from enums import AnswerTypeEnum, MediaKindEnum, QuestionTypeEnum
from errors.request import BadRequestError, ForbiddenError, NotFoundError, ResourceConflictError
from schemas.prompt.category import (
    PromptCategoryCreateSchema,
    PromptCategoryFilterSchema,
    PromptCategoryInDBSchema,
    PromptCategoryUpdateSchema,
)
from schemas.prompt.nested import (
    PaginatedPromptCategoryWithPromptsInDBSchema,
    PromptCategoryWithPromptsInDBSchema,
)
from schemas.prompt.prompt import (
    PromptCreateSchema,
    PromptInDBSchema,
    PromptUpdateSchema,
)
from schemas.user.base import UserPublicSchema
from services.media import MediaService


class PromptService:
    def __init__(self, uow: Annotated[UnitOfWork, Depends()]):
        self._uow = uow

    async def search_prompt_category(
        self,
        filters: PromptCategoryFilterSchema,
        user: UserPublicSchema,
    ) -> PaginatedPromptCategoryWithPromptsInDBSchema:
        async with self._uow as uow:
            result = await uow.prompt_category_repo.search_prompt_categories(
                filters=filters,
            )
        return result.model_copy(
            update={
                "contents": [
                    _redact_category_prompts(category, user.id) for category in result.contents
                ],
            },
        )

    async def get_prompt_category(
        self,
        category_id: int,
        user: UserPublicSchema,
    ) -> PromptCategoryWithPromptsInDBSchema:
        async with self._uow as uow:
            category = await uow.prompt_category_repo.select_prompt_category(
                category_id=category_id,
            )
        if category is None:
            raise NotFoundError(f"Prompt category {category_id} not found")
        if category.owner_id != user.id:
            raise ForbiddenError("Only the owner can view this prompt category")
        return category

    async def create_prompt_category(
        self,
        schema: PromptCategoryCreateSchema,
        owner_id: int,
    ) -> PromptCategoryInDBSchema:
        async with self._uow as uow:
            return await uow.prompt_category_repo.insert_prompt_category(
                schema=schema,
                owner_id=owner_id,
            )

    async def update_prompt_category(
        self,
        category_id: int,
        user: UserPublicSchema,
        schema: PromptCategoryUpdateSchema,
    ) -> PromptCategoryWithPromptsInDBSchema:
        async with self._uow as uow:
            await self._ensure_owned_category(uow, category_id, user)
            updated = await uow.prompt_category_repo.update_prompt_category(
                category_id,
                schema,
            )
        if updated is None:
            raise NotFoundError(f"Prompt category {category_id} not found")
        return updated

    async def delete_prompt_category(
        self,
        category_id: int,
        user: UserPublicSchema,
    ) -> None:
        async with self._uow as uow:
            await self._ensure_owned_category(uow, category_id, user)
            await uow.prompt_category_repo.delete_prompt_category(category_id)

    async def create_prompt(
        self,
        category_id: int,
        schema: PromptCreateSchema,
        user: UserPublicSchema,
    ) -> PromptInDBSchema:
        async with self._uow as uow:
            category = await self._ensure_owned_category(uow, category_id, user)
            if any(p.order == schema.order for p in category.prompts):
                raise ResourceConflictError(
                    f"Order {schema.order} is already taken in category {category_id}",
                )
            await self._validate_prompt_media(
                uow=uow,
                user=user,
                question_type=schema.question_type,
                question_media_asset_id=schema.question_media_asset_id,
                answer_type=schema.answer_type,
                answer_media_asset_id=schema.answer_media_asset_id,
            )
            return await uow.prompt_repo.insert_prompt(
                category_id=category_id,
                schema=schema,
            )

    async def update_prompt(
        self,
        category_id: int,
        prompt_id: int,
        user: UserPublicSchema,
        schema: PromptUpdateSchema,
    ) -> PromptInDBSchema:
        async with self._uow as uow:
            category = await self._ensure_owned_category(
                uow,
                category_id,
                user,
                prompt_id=prompt_id,
            )
            existing = next(prompt for prompt in category.prompts if prompt.id == prompt_id)
            question_type = schema.question_type or existing.question_type
            answer_type = schema.answer_type or existing.answer_type
            question_media_asset_id = (
                schema.question_media_asset_id
                if "question_media_asset_id" in schema.model_fields_set
                else existing.question_media_asset_id
            )
            answer_media_asset_id = (
                schema.answer_media_asset_id
                if "answer_media_asset_id" in schema.model_fields_set
                else existing.answer_media_asset_id
            )
            await self._validate_prompt_media(
                uow=uow,
                user=user,
                question_type=question_type,
                question_media_asset_id=question_media_asset_id,
                answer_type=answer_type,
                answer_media_asset_id=answer_media_asset_id,
            )
            prompt = await uow.prompt_repo.update_prompt(prompt_id, schema)
        if prompt is None:
            raise NotFoundError(f"Prompt {prompt_id} not found")
        return prompt

    async def delete_prompt(
        self,
        category_id: int,
        prompt_id: int,
        user: UserPublicSchema,
    ) -> None:
        async with self._uow as uow:
            await self._ensure_owned_category(
                uow,
                category_id,
                user,
                prompt_id=prompt_id,
            )
            await uow.prompt_repo.delete_prompt(prompt_id)

    @classmethod
    async def _ensure_owned_category(
        cls,
        uow: UnitOfWork,
        category_id: int,
        user: UserPublicSchema,
        prompt_id: int | None = None,
    ) -> PromptCategoryWithPromptsInDBSchema:
        """
        Load a category by id and assert (1) it exists, (2) ``user`` owns it,
        and optionally (3) ``prompt_id`` belongs to it. Returns the category
        (with prompts eagerly loaded) so callers can reuse it without a
        second query.

        :param uow: active unit of work (already inside ``async with``)
        :param category_id: prompt category primary key to load
        :param user: authenticated user whose id must match ``owner_id``
        :param prompt_id: when supplied, also asserts the prompt belongs to
            this category
        :return: loaded category with its prompts
        :raises NotFoundError: category missing, or ``prompt_id`` not in it
        :raises ForbiddenError: ``user`` is not the category owner
        """
        category = await uow.prompt_category_repo.select_prompt_category(
            category_id=category_id,
        )
        if category is None:
            raise NotFoundError(f"Prompt category {category_id} not found")
        if category.owner_id != user.id:
            raise ForbiddenError(
                "Only the owner can modify this prompt category",
            )
        if prompt_id is not None and not any(p.id == prompt_id for p in category.prompts):
            raise NotFoundError(
                f"Prompt {prompt_id} not found in category {category_id}",
            )
        return category

    @classmethod
    async def _validate_prompt_media(
        cls,
        *,
        uow: UnitOfWork,
        user: UserPublicSchema,
        question_type: QuestionTypeEnum,
        question_media_asset_id: int | None,
        answer_type: AnswerTypeEnum,
        answer_media_asset_id: int | None,
    ) -> None:
        cls._validate_content_media_pair(
            question_type,
            question_media_asset_id,
            "question_media_asset_id",
        )
        cls._validate_content_media_pair(
            answer_type,
            answer_media_asset_id,
            "answer_media_asset_id",
        )
        await MediaService.ensure_owned_asset(
            uow=uow,
            asset_id=question_media_asset_id,
            expected_kind=_media_kind_for_content_type(question_type),
            user_id=user.id,
            field_name="question_media_asset_id",
        )
        await MediaService.ensure_owned_asset(
            uow=uow,
            asset_id=answer_media_asset_id,
            expected_kind=_media_kind_for_content_type(answer_type),
            user_id=user.id,
            field_name="answer_media_asset_id",
        )

    @staticmethod
    def _validate_content_media_pair(
        content_type: QuestionTypeEnum | AnswerTypeEnum,
        asset_id: int | None,
        field_name: str,
    ) -> None:
        if _media_kind_for_content_type(content_type) is None and asset_id is not None:
            raise BadRequestError(f"{field_name} must be empty for text content")
        if _media_kind_for_content_type(content_type) is not None and asset_id is None:
            raise BadRequestError(f"{field_name} is required for media content")


def _media_kind_for_content_type(
    content_type: QuestionTypeEnum | AnswerTypeEnum,
) -> MediaKindEnum | None:
    if content_type.value == QuestionTypeEnum.TEXT:
        return None
    return MediaKindEnum(content_type.value)


def _redact_category_prompts(
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
