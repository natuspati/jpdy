from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.prompt import Prompt
from schemas.prompt.prompt import (
    PromptCreateSchema,
    PromptInDBSchema,
    PromptUpdateSchema,
)
from utils.model_validation import validate_model


class PromptRepo:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def insert_prompt(
        self,
        category_id: int,
        schema: PromptCreateSchema,
    ) -> PromptInDBSchema:
        """
        Insert a new prompt using SQL ``INSERT ... RETURNING``.

        :param category_id: id of the category the prompt belongs to
        :param schema: validated prompt create payload; ``order`` is required
            and bounded by ``NUM_PROMPTS_IN_CATEGORY`` (uniqueness within the
            category is enforced by the service layer).
        :return: the inserted prompt as ``PromptInDBSchema``
        """
        stmt = (
            insert(Prompt)
            .values(category_id=category_id, **schema.model_dump())
            .returning(Prompt.id)
        )
        prompt_id = (await self._session.execute(stmt)).scalar_one()
        prompt = await self.select_prompt(prompt_id)
        assert prompt is not None
        return prompt

    async def update_prompt(
        self,
        prompt_id: int,
        schema: PromptUpdateSchema,
    ) -> PromptInDBSchema | None:
        """
        Update an existing prompt; only fields explicitly set on the schema are
        applied (``model_dump(exclude_unset=True)``). The ``order`` column is
        not updatable here — it is managed via
        :meth:`PromptCategoryRepo.update_prompt_category` with ``prompt_order``.

        :param prompt_id: prompt primary key
        :param schema: validated update payload
        :return: the updated prompt, or ``None`` if no prompt matches
        """
        values = schema.model_dump(exclude_unset=True)
        stmt = update(Prompt).where(Prompt.id == prompt_id).values(**values).returning(Prompt.id)
        updated_id = (await self._session.execute(stmt)).scalar_one_or_none()
        if updated_id is None:
            return None
        return await self.select_prompt(updated_id)

    async def select_prompt(self, prompt_id: int) -> PromptInDBSchema | None:
        stmt = (
            select(Prompt)
            .where(Prompt.id == prompt_id)
            .options(
                selectinload(Prompt.question_media_asset),
                selectinload(Prompt.answer_media_asset),
            )
        )
        prompt = (await self._session.execute(stmt)).scalar_one_or_none()
        return validate_model(prompt, PromptInDBSchema)

    async def delete_prompt(self, prompt_id: int) -> bool:
        """
        Delete a prompt by id.

        :param prompt_id: prompt primary key
        :return: ``True`` if a row was deleted, ``False`` if no prompt matched
        """
        stmt = delete(Prompt).where(Prompt.id == prompt_id)
        result = await self._session.execute(stmt)
        return result.rowcount > 0
