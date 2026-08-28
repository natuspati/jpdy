from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from auth import get_current_user
from schemas.error import ErrorResponse
from schemas.lobby.base import (
    LobbyFilterSchema,
    LobbyInDBSchema,
    LobbyUpdateSchema,
)
from schemas.lobby.nested import (
    LobbyWithCategoriesInDBSchema,
    PaginatedLobbyWithCategoriesInDBSchema,
)
from schemas.user.base import UserInDBSchema
from services import LobbyService
from utils.route_response import generate_responses

router = APIRouter(prefix="/lobby", tags=["lobby"])

_UNAUTHORIZED = ErrorResponse(
    status.HTTP_401_UNAUTHORIZED,
    "Missing, expired, or invalid bearer token",
)
_LOBBY_NOT_FOUND = ErrorResponse(
    status.HTTP_404_NOT_FOUND,
    "Lobby not found",
)
_FORBIDDEN_LOBBY = ErrorResponse(
    status.HTTP_403_FORBIDDEN,
    "Only the owner can modify this lobby",
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
async def search_lobbies(
    filters: Annotated[LobbyFilterSchema, Query()],
    service: Annotated[LobbyService, Depends()],
) -> PaginatedLobbyWithCategoriesInDBSchema:
    return await service.search_lobbies(filters=filters)


@router.get(
    "/{lobby_id}",
    responses=generate_responses(
        _UNAUTHORIZED,
        _LOBBY_NOT_FOUND,
    ),
    dependencies=[Depends(get_current_user)],
)
async def get_lobby(
    lobby_id: int,
    service: Annotated[LobbyService, Depends()],
) -> LobbyWithCategoriesInDBSchema:
    return await service.get_lobby(lobby_id=lobby_id)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses=generate_responses(_UNAUTHORIZED),
)
async def create_lobby(
    current_user: Annotated[UserInDBSchema, Depends(get_current_user)],
    service: Annotated[LobbyService, Depends()],
) -> LobbyInDBSchema:
    return await service.create_lobby(owner_id=current_user.id)


@router.patch(
    "/{lobby_id}",
    responses=generate_responses(
        _UNAUTHORIZED,
        _FORBIDDEN_LOBBY,
        _LOBBY_NOT_FOUND,
        ErrorResponse(
            status.HTTP_400_BAD_REQUEST,
            "REST may only transition CREATED lobbies to WAITING_START. "
            "Categories may only be changed while CREATED and every attached "
            "category must contain five uniquely ordered text prompts.",
        ),
        ErrorResponse(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Invalid lobby update payload",
        ),
    ),
)
async def update_lobby(
    lobby_id: int,
    schema: LobbyUpdateSchema,
    current_user: Annotated[UserInDBSchema, Depends(get_current_user)],
    service: Annotated[LobbyService, Depends()],
) -> LobbyWithCategoriesInDBSchema:
    return await service.update_lobby(
        lobby_id=lobby_id,
        user=current_user,
        schema=schema,
    )


@router.delete(
    "/{lobby_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=generate_responses(
        _UNAUTHORIZED,
        _FORBIDDEN_LOBBY,
        _LOBBY_NOT_FOUND,
        ErrorResponse(
            status.HTTP_400_BAD_REQUEST,
            "Only lobbies in the CREATED state can be deleted",
        ),
    ),
)
async def delete_lobby(
    lobby_id: int,
    current_user: Annotated[UserInDBSchema, Depends(get_current_user)],
    service: Annotated[LobbyService, Depends()],
) -> None:
    await service.delete_lobby(
        lobby_id=lobby_id,
        user=current_user,
    )
