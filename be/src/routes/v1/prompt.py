from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from auth import get_current_user
from schemas.error import ErrorResponse
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
from schemas.user.base import UserInDBSchema
from services import PromptService
from utils.route_response import generate_responses

router = APIRouter(prefix="/category", tags=["prompt"])

_UNAUTHORIZED = ErrorResponse(
    status.HTTP_401_UNAUTHORIZED,
    "Missing, expired, or invalid bearer token",
)
_CATEGORY_NOT_FOUND = ErrorResponse(
    status.HTTP_404_NOT_FOUND,
    "Prompt category not found",
)
_FORBIDDEN_CATEGORY = ErrorResponse(
    status.HTTP_403_FORBIDDEN,
    "Only the owner can modify this prompt category",
)


@router.get(
    "",
    responses=generate_responses(
        _UNAUTHORIZED,
        ErrorResponse(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Invalid search parameters",
        ),
    ),
    dependencies=[Depends(get_current_user)],
)
async def search_prompt_categories(
    filters: Annotated[PromptCategoryFilterSchema, Query()],
    current_user: Annotated[UserInDBSchema, Depends(get_current_user)],
    service: Annotated[PromptService, Depends()],
) -> PaginatedPromptCategoryWithPromptsInDBSchema:
    return await service.search_prompt_category(filters=filters, user=current_user)


@router.get(
    "/{category_id}",
    responses=generate_responses(
        _UNAUTHORIZED,
        _FORBIDDEN_CATEGORY,
        _CATEGORY_NOT_FOUND,
    ),
    dependencies=[Depends(get_current_user)],
)
async def get_prompt_category(
    category_id: int,
    current_user: Annotated[UserInDBSchema, Depends(get_current_user)],
    service: Annotated[PromptService, Depends()],
) -> PromptCategoryWithPromptsInDBSchema:
    return await service.get_prompt_category(category_id, current_user)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses=generate_responses(
        _UNAUTHORIZED,
        ErrorResponse(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Invalid prompt category create payload",
        ),
    ),
)
async def create_prompt_category(
    schema: PromptCategoryCreateSchema,
    current_user: Annotated[UserInDBSchema, Depends(get_current_user)],
    service: Annotated[PromptService, Depends()],
) -> PromptCategoryInDBSchema:
    return await service.create_prompt_category(
        schema=schema,
        owner_id=current_user.id,
    )


@router.patch(
    "/{category_id}",
    responses=generate_responses(
        _UNAUTHORIZED,
        _FORBIDDEN_CATEGORY,
        _CATEGORY_NOT_FOUND,
        ErrorResponse(
            status.HTTP_400_BAD_REQUEST,
            "Invalid prompt_order mapping (orders not in 1..N, duplicates, "
            "or prompts not in this category)",
        ),
        ErrorResponse(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Invalid prompt category update payload",
        ),
    ),
)
async def update_prompt_category(
    category_id: int,
    schema: PromptCategoryUpdateSchema,
    current_user: Annotated[UserInDBSchema, Depends(get_current_user)],
    service: Annotated[PromptService, Depends()],
) -> PromptCategoryWithPromptsInDBSchema:
    return await service.update_prompt_category(
        category_id=category_id,
        user=current_user,
        schema=schema,
    )


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=generate_responses(
        _UNAUTHORIZED,
        _FORBIDDEN_CATEGORY,
        _CATEGORY_NOT_FOUND,
    ),
)
async def delete_prompt_category(
    category_id: int,
    current_user: Annotated[UserInDBSchema, Depends(get_current_user)],
    service: Annotated[PromptService, Depends()],
) -> None:
    await service.delete_prompt_category(
        category_id=category_id,
        user=current_user,
    )


@router.post(
    "/{category_id}/prompts",
    status_code=status.HTTP_201_CREATED,
    responses=generate_responses(
        _UNAUTHORIZED,
        _FORBIDDEN_CATEGORY,
        _CATEGORY_NOT_FOUND,
        ErrorResponse(
            status.HTTP_409_CONFLICT,
            "Order already taken in this category",
        ),
        ErrorResponse(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Invalid prompt create payload (missing fields or order outside 1..N)",
        ),
    ),
)
async def create_prompt(
    category_id: int,
    schema: PromptCreateSchema,
    current_user: Annotated[UserInDBSchema, Depends(get_current_user)],
    service: Annotated[PromptService, Depends()],
) -> PromptInDBSchema:
    return await service.create_prompt(
        category_id=category_id,
        schema=schema,
        user=current_user,
    )


@router.patch(
    "/{category_id}/prompts/{prompt_id}",
    responses=generate_responses(
        _UNAUTHORIZED,
        _FORBIDDEN_CATEGORY,
        ErrorResponse(
            status.HTTP_404_NOT_FOUND,
            "Prompt not found in this category",
        ),
        ErrorResponse(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Invalid prompt update payload",
        ),
    ),
)
async def update_prompt(
    category_id: int,
    prompt_id: int,
    current_user: Annotated[UserInDBSchema, Depends(get_current_user)],
    schema: PromptUpdateSchema,
    service: Annotated[PromptService, Depends()],
) -> PromptInDBSchema:
    return await service.update_prompt(
        prompt_id=prompt_id,
        category_id=category_id,
        user=current_user,
        schema=schema,
    )


@router.delete(
    "/{category_id}/prompts/{prompt_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=generate_responses(
        _UNAUTHORIZED,
        _FORBIDDEN_CATEGORY,
        _CATEGORY_NOT_FOUND,
        ErrorResponse(
            status.HTTP_404_NOT_FOUND,
            "Prompt not found in this category",
        ),
    ),
)
async def delete_prompt(
    category_id: int,
    prompt_id: int,
    current_user: Annotated[UserInDBSchema, Depends(get_current_user)],
    service: Annotated[PromptService, Depends()],
) -> None:
    await service.delete_prompt(
        category_id=category_id,
        prompt_id=prompt_id,
        user=current_user,
    )
