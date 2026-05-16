from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from auth.authenticate import get_current_user
from schemas.error import ErrorResponse
from schemas.token import TokenSchema
from schemas.user.base import UserCreateSchema, UserInDBSchema, UserPublicSchema
from schemas.user.nested import UserWithPromptsLobbiesPublicSchema
from services.user import UserService
from utils.route_response import generate_responses

router = APIRouter(prefix="/user", tags=["user"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    responses=generate_responses(
        ErrorResponse(
            status.HTTP_409_CONFLICT,
            "Username already taken",
        ),
        ErrorResponse(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Invalid registration payload",
        ),
    ),
)
async def register(
    schema: UserCreateSchema,
    service: Annotated[UserService, Depends()],
) -> UserPublicSchema:
    return await service.register(schema)


@router.post(
    "/sign-in",
    responses=generate_responses(
        ErrorResponse(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid username or password",
        ),
        ErrorResponse(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Invalid sign-in form",
        ),
    ),
)
async def sign_in(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: Annotated[UserService, Depends()],
) -> TokenSchema:
    return await service.sign_in(form.username, form.password)


@router.get(
    "/me",
    responses=generate_responses(
        ErrorResponse(
            status.HTTP_401_UNAUTHORIZED,
            "Missing, expired, or invalid bearer token",
        ),
        ErrorResponse(
            status.HTTP_404_NOT_FOUND,
            "Authenticated user no longer exists",
        ),
    ),
)
async def me(
    current_user: Annotated[UserInDBSchema, Depends(get_current_user)],
    service: Annotated[UserService, Depends()],
) -> UserWithPromptsLobbiesPublicSchema:
    return await service.get_user(current_user.id)
