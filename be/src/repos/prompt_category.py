from sqlalchemy import delete, distinct, func, insert, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from configs.constants import NUM_PROMPTS_IN_CATEGORY
from enums.prompt import AnswerTypeEnum, QuestionTypeEnum
from errors.request import BadRequestError
from models.prompt import Prompt
from models.prompt_category import PromptCategory
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
from utils.model_validation import validate_model


class PromptCategoryRepo:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def search_prompt_categories(
        self,
        filters: PromptCategoryFilterSchema,
    ) -> PaginatedPromptCategoryWithPromptsInDBSchema:
        """
        Search prompt categories with pagination, returning each category with
        its joined prompts.

        Issues two queries against the same filtered base query: a ``count(*)``
        over the filter-only subquery for the total, and a paginated select
        with ``selectinload(prompts)`` for the page of rows. ``is_complete``
        filters on correlated total-prompt, valid-order, text-prompt, and
        distinct-order counts. A category is complete only when all four equal
        ``NUM_PROMPTS_IN_CATEGORY``; otherwise it is incomplete.

        :param filters: validated search/pagination payload
        :return: page of categories with prompts plus total count
        """
        total_prompt_count_subq = (
            select(func.count(Prompt.id))
            .where(Prompt.category_id == PromptCategory.id)
            .correlate(PromptCategory)
            .scalar_subquery()
        )
        valid_prompt_count_subq = (
            select(func.count(Prompt.id))
            .where(
                Prompt.category_id == PromptCategory.id,
                Prompt.order.between(1, NUM_PROMPTS_IN_CATEGORY),
            )
            .correlate(PromptCategory)
            .scalar_subquery()
        )
        unique_order_count_subq = (
            select(func.count(distinct(Prompt.order)))
            .where(
                Prompt.category_id == PromptCategory.id,
                Prompt.order.between(1, NUM_PROMPTS_IN_CATEGORY),
            )
            .correlate(PromptCategory)
            .scalar_subquery()
        )
        text_prompt_count_subq = (
            select(func.count(Prompt.id))
            .where(
                Prompt.category_id == PromptCategory.id,
                Prompt.question_type == QuestionTypeEnum.TEXT,
                Prompt.answer_type == AnswerTypeEnum.TEXT,
            )
            .correlate(PromptCategory)
            .scalar_subquery()
        )

        conditions = []
        if filters.ids is not None:
            conditions.append(PromptCategory.id.in_(filters.ids))
        if filters.name is not None:
            conditions.append(PromptCategory.name.ilike(f"%{filters.name}%"))
        if filters.owner_ids is not None:
            conditions.append(PromptCategory.owner_id.in_(filters.owner_ids))
        if filters.updated_at_start is not None:
            conditions.append(PromptCategory.updated_at >= filters.updated_at_start)
        if filters.updated_at_end is not None:
            conditions.append(PromptCategory.updated_at <= filters.updated_at_end)
        if filters.is_complete is not None:
            if filters.is_complete:
                conditions.extend(
                    [
                        total_prompt_count_subq == NUM_PROMPTS_IN_CATEGORY,
                        valid_prompt_count_subq == NUM_PROMPTS_IN_CATEGORY,
                        text_prompt_count_subq == NUM_PROMPTS_IN_CATEGORY,
                        unique_order_count_subq == NUM_PROMPTS_IN_CATEGORY,
                    ],
                )
            else:
                conditions.append(
                    or_(
                        total_prompt_count_subq != NUM_PROMPTS_IN_CATEGORY,
                        valid_prompt_count_subq != NUM_PROMPTS_IN_CATEGORY,
                        text_prompt_count_subq != NUM_PROMPTS_IN_CATEGORY,
                        unique_order_count_subq != NUM_PROMPTS_IN_CATEGORY,
                    ),
                )

        base_query = select(PromptCategory).where(*conditions)

        total_query = select(func.count()).select_from(base_query.subquery())
        total = (await self._session.execute(total_query)).scalar_one()

        paginated_query = (
            base_query.options(selectinload(PromptCategory.prompts))
            .order_by(PromptCategory.updated_at.desc(), PromptCategory.id.desc())
            .limit(filters.limit)
            .offset(filters.offset)
        )
        rows = (await self._session.execute(paginated_query)).scalars().all()
        contents = validate_model(rows, PromptCategoryWithPromptsInDBSchema)

        return PaginatedPromptCategoryWithPromptsInDBSchema(
            contents=contents,
            total=total,
            page=filters.page,
            size=filters.size,
        )

    async def select_prompt_category(
        self,
        category_id: int,
    ) -> PromptCategoryWithPromptsInDBSchema | None:
        """
        Select a prompt category by id with its prompts eagerly loaded.

        :param category_id: prompt category primary key
        :return: matched category with prompts, or ``None`` if no category matches
        """
        query = (
            select(PromptCategory)
            .where(PromptCategory.id == category_id)
            .options(selectinload(PromptCategory.prompts))
        )
        category = (await self._session.execute(query)).scalar_one_or_none()
        return validate_model(category, PromptCategoryWithPromptsInDBSchema)

    async def insert_prompt_category(
        self,
        schema: PromptCategoryCreateSchema,
        owner_id: int,
    ) -> PromptCategoryInDBSchema:
        """
        Insert a new prompt category using SQL ``INSERT ... RETURNING``.

        Prompts are not created here; use :meth:`PromptRepo.insert_prompt`
        for that.

        :param schema: validated prompt category create payload
        :param owner_id: id of the user who will own the new category
        :return: the inserted prompt category as ``PromptCategoryInDBSchema``
        """
        stmt = (
            insert(PromptCategory)
            .values(name=schema.name, owner_id=owner_id)
            .returning(PromptCategory)
        )
        category = (await self._session.execute(stmt)).scalar_one()
        return validate_model(category, PromptCategoryInDBSchema)

    async def update_prompt_category(
        self,
        category_id: int,
        schema: PromptCategoryUpdateSchema,
    ) -> PromptCategoryWithPromptsInDBSchema | None:
        """
        Update an existing prompt category. Only the ``name`` column on the
        category itself can be changed; ``prompt_order`` is a side-channel for
        re-ordering the prompts that belong to this category.

        ``prompt_order`` is a mapping of ``{prompt_id: new_order}``. Validation:
        all referenced prompts must belong to ``category_id``, every supplied
        order must lie in ``1..NUM_PROMPTS_IN_CATEGORY``, and the orders must
        be pairwise unique within the mapping. Uniqueness of ``order`` across
        the category overall is the caller's responsibility — the DB allows
        temporary ``NULL`` / negative values to support staged reorders.

        After applying changes the category is re-fetched via
        :meth:`select_prompt_category` so the response includes the prompts
        with their (potentially new) ordering.

        :param category_id: prompt category primary key
        :param schema: validated update payload
        :return: the updated category with prompts, or ``None`` if no category
            matches
        """
        if schema.prompt_order is not None:
            await self._apply_prompt_order(category_id, schema.prompt_order)

        update_values = schema.model_dump(
            exclude_unset=True,
            exclude={"prompt_order"},
        )
        if update_values:
            stmt = (
                update(PromptCategory)
                .where(PromptCategory.id == category_id)
                .values(**update_values)
            )
            result = await self._session.execute(stmt)
            if result.rowcount == 0:
                return None

        return await self.select_prompt_category(category_id)

    async def delete_prompt_category(self, category_id: int) -> bool:
        """
        Delete a prompt category by id. Prompts that belong to the category
        are cascaded by the ``ON DELETE CASCADE`` constraint on
        ``prompt.category_id``.

        :param category_id: prompt category primary key
        :return: ``True`` if a row was deleted, ``False`` if no category matched
        """
        stmt = delete(PromptCategory).where(PromptCategory.id == category_id)
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def _apply_prompt_order(
        self,
        category_id: int,
        prompt_order: dict[int, int],
    ) -> None:
        if not prompt_order:
            return

        new_orders = list(prompt_order.values())
        if len(set(new_orders)) != len(new_orders):
            raise BadRequestError("Prompt orders must be unique within the mapping")
        for order_value in new_orders:
            if not 1 <= order_value <= NUM_PROMPTS_IN_CATEGORY:
                raise BadRequestError(
                    f"Prompt order must be between 1 and {NUM_PROMPTS_IN_CATEGORY}",
                )

        prompt_ids = list(prompt_order.keys())
        owned_query = select(Prompt.id).where(
            Prompt.id.in_(prompt_ids),
            Prompt.category_id == category_id,
        )
        owned_ids = set(
            (await self._session.execute(owned_query)).scalars().all(),
        )
        missing = set(prompt_ids) - owned_ids
        if missing:
            raise BadRequestError(
                f"Prompts {sorted(missing)} do not belong to category {category_id}",
            )

        for prompt_id, new_order in prompt_order.items():
            stmt = update(Prompt).where(Prompt.id == prompt_id).values(order=new_order)
            await self._session.execute(stmt)
