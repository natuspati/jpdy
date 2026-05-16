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
    PaginatedPromptCategoryWithPromptsInDBSchema,
    PromptCategoryWithPromptsInDBSchema,
)
from schemas.prompt.prompt import (
    PromptCreateSchema,
    PromptInDBSchema,
    PromptUpdateSchema,
)
from schemas.user.base import UserPublicSchema


class PromptService:
    def __init__(self, uow: Annotated[UnitOfWork, Depends()]):
        self._uow = uow

    async def search_prompt_category(
        self,
        filters: PromptCategoryFilterSchema,
    ) -> PaginatedPromptCategoryWithPromptsInDBSchema:
        async with self._uow as uow:
            return await uow.prompt_category_repo.search_prompt_categories(
                filters=filters,
            )

    async def get_prompt_category(
        self,
        category_id: int,
    ) -> PromptCategoryWithPromptsInDBSchema:
        async with self._uow as uow:
            category = await uow.prompt_category_repo.select_prompt_category(
                category_id=category_id,
            )
        if category is None:
            raise NotFoundError(f"Prompt category {category_id} not found")
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
            await self._ensure_owned_category(
                uow,
                category_id,
                user,
                prompt_id=prompt_id,
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
