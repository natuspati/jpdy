from typing import Annotated

from fastapi import Depends

from database import UnitOfWork
from errors.request import NotFoundError
from schemas.prompt.category import (
    PromptCategoryFilterSchema,
    PromptCategoryInDBSchema,
    PromptCategoryUpdateSchema,
)
from schemas.prompt.nested import (
    PaginatedPromptCategoryWithPromptsInDBSchema,
    PromptCategoryWithPromptsInDBSchema,
)
from schemas.prompt.prompt import PromptInDBSchema, PromptUpdateSchema


class PromptService:
    def __init__(self, uow: Annotated[UnitOfWork, Depends()]):
        self._uow = uow

    async def search_prompt_category(
        self,
        filters: PromptCategoryFilterSchema,
    ) -> PaginatedPromptCategoryWithPromptsInDBSchema:
        async with self._uow:
            return await self._uow.prompt_category_repo.search_prompt_categories(
                filters,
            )

    async def get_prompt_category(
        self,
        category_id: int,
    ) -> PromptCategoryWithPromptsInDBSchema:
        async with self._uow:
            category = await self._uow.prompt_category_repo.select_prompt_category(
                category_id,
            )
        if category is None:
            raise NotFoundError(f"Prompt category {category_id} not found")
        return category

    async def update_prompt_category(
        self,
        category_id: int,
        schema: PromptCategoryUpdateSchema,
    ) -> PromptCategoryInDBSchema:
        async with self._uow:
            category = await self._uow.prompt_category_repo.update_prompt_category(
                category_id,
                schema,
            )
        if category is None:
            raise NotFoundError(f"Prompt category {category_id} not found")
        return category

    async def update_prompt(
        self,
        prompt_id: int,
        schema: PromptUpdateSchema,
    ) -> PromptInDBSchema:
        async with self._uow:
            prompt = await self._uow.prompt_repo.update_prompt(prompt_id, schema)
        if prompt is None:
            raise NotFoundError(f"Prompt {prompt_id} not found")
        return prompt
