from typing import Annotated

from fastapi import Depends

from database import UnitOfWork
from errors.request import ForbiddenError, NotFoundError, ResourceConflictError
from schemas.prompt.category import (
    PromptCategoryCreateSchema,
    PromptCategoryFilterSchema,
    PromptCategoryInDBSchema,
    PromptCategoryUpdateSchema,
)
from schemas.prompt.nested import (
    PaginatedPromptCategoryResponseSchema,
    PromptCategoryResponseSchema,
)
from schemas.prompt.prompt import (
    PromptCreateSchema,
    PromptResponseSchema,
    PromptUpdateSchema,
)
from schemas.user.base import UserPublicSchema
from utils.prompt import (
    build_prompt_category_response,
    build_prompt_response,
    ensure_owned_category,
    redact_category_prompts,
    validate_prompt_media,
    validate_prompt_order,
)


class PromptService:
    def __init__(self, uow: Annotated[UnitOfWork, Depends()]):
        self._uow = uow

    async def search_prompt_category(
        self,
        filters: PromptCategoryFilterSchema,
        user: UserPublicSchema,
    ) -> PaginatedPromptCategoryResponseSchema:
        async with self._uow as uow:
            result = await uow.prompt_category_repo.search_prompt_categories(filters=filters)
        return PaginatedPromptCategoryResponseSchema(
            contents=[
                build_prompt_category_response(redact_category_prompts(category, user.id))
                for category in result.contents
            ],
            total=result.total,
            page=result.page,
            size=result.size,
        )

    async def get_prompt_category(
        self,
        category_id: int,
        user: UserPublicSchema,
    ) -> PromptCategoryResponseSchema:
        async with self._uow as uow:
            category = await uow.prompt_category_repo.select_prompt_category(
                category_id=category_id,
            )
        if category is None:
            raise NotFoundError(f"Prompt category {category_id} not found")
        if category.owner_id != user.id:
            raise ForbiddenError("Only the owner can view this prompt category")
        return build_prompt_category_response(category)

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
    ) -> PromptCategoryResponseSchema:
        async with self._uow as uow:
            category = await ensure_owned_category(uow, category_id, user)
            if schema.prompt_order is not None:
                validate_prompt_order(category_id, schema.prompt_order, category)
            updated = await uow.prompt_category_repo.update_prompt_category(category_id, schema)
        if updated is None:
            raise NotFoundError(f"Prompt category {category_id} not found")
        return build_prompt_category_response(updated)

    async def delete_prompt_category(
        self,
        category_id: int,
        user: UserPublicSchema,
    ) -> None:
        async with self._uow as uow:
            await ensure_owned_category(uow, category_id, user)
            await uow.prompt_category_repo.delete_prompt_category(category_id)

    async def create_prompt(
        self,
        category_id: int,
        schema: PromptCreateSchema,
        user: UserPublicSchema,
    ) -> PromptResponseSchema:
        async with self._uow as uow:
            category = await ensure_owned_category(uow, category_id, user)
            if any(prompt.order == schema.order for prompt in category.prompts):
                raise ResourceConflictError(
                    f"Order {schema.order} is already taken in category {category_id}",
                )
            await validate_prompt_media(
                uow=uow,
                user=user,
                question_type=schema.question_type,
                question_media_asset_id=schema.question_media_asset_id,
                answer_type=schema.answer_type,
                answer_media_asset_id=schema.answer_media_asset_id,
            )
            prompt = await uow.prompt_repo.insert_prompt(category_id=category_id, schema=schema)
        return build_prompt_response(prompt)

    async def update_prompt(
        self,
        category_id: int,
        prompt_id: int,
        user: UserPublicSchema,
        schema: PromptUpdateSchema,
    ) -> PromptResponseSchema:
        async with self._uow as uow:
            category = await ensure_owned_category(uow, category_id, user, prompt_id=prompt_id)
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
            await validate_prompt_media(
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
        return build_prompt_response(prompt)

    async def delete_prompt(
        self,
        category_id: int,
        prompt_id: int,
        user: UserPublicSchema,
    ) -> None:
        async with self._uow as uow:
            await ensure_owned_category(uow, category_id, user, prompt_id=prompt_id)
            await uow.prompt_repo.delete_prompt(prompt_id)
