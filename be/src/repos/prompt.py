from sqlalchemy import delete, insert, update
from sqlalchemy.ext.asyncio import AsyncSession

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
            insert(Prompt).values(category_id=category_id, **schema.model_dump()).returning(Prompt)
        )
        prompt = (await self._session.execute(stmt)).scalar_one()
        return validate_model(prompt, PromptInDBSchema)

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
        stmt = update(Prompt).where(Prompt.id == prompt_id).values(**values).returning(Prompt)
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
