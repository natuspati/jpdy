#!/usr/bin/env python3
"""Idempotently seed the configured database with local Jeopardy data."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.session import async_session_maker
from models.prompt import Prompt
from models.prompt_category import PromptCategory
from models.user import User
from utils.auth import hash_password


@dataclass(frozen=True)
class SeedUser:
    username: str
    password: str


@dataclass(frozen=True)
class SeedPrompt:
    question: str
    answer: str


@dataclass(frozen=True)
class SeedCategory:
    name: str
    prompts: tuple[SeedPrompt, SeedPrompt, SeedPrompt, SeedPrompt, SeedPrompt]


USERS: Final = (
    SeedUser(username="host", password="host123"),
    SeedUser(username="alice", password="alice123"),
    SeedUser(username="bob", password="bob123"),
    SeedUser(username="carol", password="carol123"),
)

CATEGORIES: Final = (
    SeedCategory(
        name="Space",
        prompts=(
            SeedPrompt("What is the largest moon in the Solar System?", "Ganymede"),
            SeedPrompt(
                "What is the nearest major galaxy to the Milky Way?",
                "Andromeda Galaxy",
            ),
            SeedPrompt("Which planet is known as the Red Planet?", "Mars"),
            SeedPrompt("Which planet is famous for its prominent rings?", "Saturn"),
            SeedPrompt("What star is at the center of the Solar System?", "The Sun"),
        ),
    ),
    SeedCategory(
        name="Felids",
        prompts=(
            SeedPrompt("Which big cat has the strongest bite force?", "Jaguar"),
            SeedPrompt("What is the largest living feline species?", "Tiger"),
            SeedPrompt("What is the largest feline that can purr?", "Cheetah"),
            SeedPrompt("Which feline is often called the king of the jungle?", "Lion"),
            SeedPrompt("Which spotted big cat is native to the Americas?", "Jaguar"),
        ),
    ),
    SeedCategory(
        name="World Capitals",
        prompts=(
            SeedPrompt("What is the capital of Japan?", "Tokyo"),
            SeedPrompt("What is the capital of Australia?", "Canberra"),
            SeedPrompt("What is the capital of Canada?", "Ottawa"),
            SeedPrompt("What is the capital of Brazil?", "Brasília"),
            SeedPrompt("What is the capital of Egypt?", "Cairo"),
        ),
    ),
    SeedCategory(
        name="Science Basics",
        prompts=(
            SeedPrompt("What is the chemical formula for water?", "H2O"),
            SeedPrompt("What force keeps planets in orbit around the Sun?", "Gravity"),
            SeedPrompt("What gas do plants take in during photosynthesis?", "Carbon dioxide"),
            SeedPrompt("What is the smallest unit of an element?", "Atom"),
            SeedPrompt("What organ pumps blood through the human body?", "Heart"),
        ),
    ),
    SeedCategory(
        name="Classic Literature",
        prompts=(
            SeedPrompt("Who wrote The Hobbit?", "J. R. R. Tolkien"),
            SeedPrompt("Who created the detective Sherlock Holmes?", "Arthur Conan Doyle"),
            SeedPrompt("Who wrote Pride and Prejudice?", "Jane Austen"),
            SeedPrompt("Who wrote 1984?", "George Orwell"),
            SeedPrompt("Who wrote The Odyssey?", "Homer"),
        ),
    ),
)


async def seed_local_database(session: AsyncSession) -> None:
    """
    Ensure fixed local users and host-owned text categories exist.

    Existing users are retained. Existing host categories with seed names are
    reconciled to their five expected prompts, so executing this after Alembic
    migrations is safe repeatedly.
    """
    users = await _ensure_users(session)
    host = users["host"]
    categories = await _load_host_categories(session, host.id)

    for seed_category in CATEGORIES:
        category = categories.get(seed_category.name)
        if category is None:
            category = PromptCategory(name=seed_category.name, owner_id=host.id)
            session.add(category)
            await session.flush()
            existing_prompts: Sequence[Prompt] = ()
        else:
            existing_prompts = category.prompts
        await _reconcile_prompts(session, existing_prompts, category.id, seed_category)


async def _ensure_users(session: AsyncSession) -> dict[str, User]:
    users: dict[str, User] = {}
    for seed_user in USERS:
        user = await session.scalar(
            select(User).where(User.username == seed_user.username),
        )
        if user is None:
            user = User(
                username=seed_user.username,
                hashed_password=hash_password(seed_user.password),
            )
            session.add(user)
            await session.flush()
        users[seed_user.username] = user
    return users


async def _load_host_categories(
    session: AsyncSession,
    host_id: int,
) -> dict[str, PromptCategory]:
    query = (
        select(PromptCategory)
        .where(PromptCategory.owner_id == host_id)
        .options(selectinload(PromptCategory.prompts))
        .order_by(PromptCategory.id)
    )
    categories = (await session.scalars(query)).all()
    categories_by_name: dict[str, PromptCategory] = {}
    for category in categories:
        categories_by_name.setdefault(category.name, category)
    return categories_by_name


async def _reconcile_prompts(
    session: AsyncSession,
    existing_prompts: Sequence[Prompt],
    category_id: int,
    seed_category: SeedCategory,
) -> None:
    prompts_by_order: dict[int, list[Prompt]] = {}
    prompts_to_delete: list[Prompt] = []
    for prompt in existing_prompts:
        if prompt.order is None:
            prompts_to_delete.append(prompt)
        else:
            prompts_by_order.setdefault(prompt.order, []).append(prompt)

    retained_prompts: dict[int, Prompt] = {}
    for order in range(1, len(seed_category.prompts) + 1):
        candidates = prompts_by_order.pop(order, [])
        if candidates:
            retained_prompts[order] = candidates[0]
            prompts_to_delete.extend(candidates[1:])

    for prompts in prompts_by_order.values():
        prompts_to_delete.extend(prompts)
    for prompt in prompts_to_delete:
        await session.delete(prompt)

    for order, seed_prompt in enumerate(seed_category.prompts, start=1):
        prompt = retained_prompts.get(order)
        if prompt is None:
            session.add(
                Prompt(
                    category_id=category_id,
                    order=order,
                    question=seed_prompt.question,
                    question_type="text",
                    answer=seed_prompt.answer,
                    answer_type="text",
                ),
            )
            continue
        prompt.question = seed_prompt.question
        prompt.question_type = "text"
        prompt.question_media_asset_id = None
        prompt.answer = seed_prompt.answer
        prompt.answer_type = "text"
        prompt.answer_media_asset_id = None


async def main() -> None:
    async with async_session_maker.begin() as session:
        await seed_local_database(session)
    print("Seed complete: 4 users, 5 host-owned categories, and 25 text prompts.")


if __name__ == "__main__":
    asyncio.run(main())
