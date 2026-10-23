from typing import Annotated

from fastapi import Depends

from configs import settings
from database import UnitOfWork
from enums.user import UserRole
from errors.request import ForbiddenError, NotFoundError
from schemas.admin import AdminUserFilterSchema, PaginatedAdminUserSchema
from services.lobby import LobbyService
from sockets.lobby_lifecycle import notify_lobbies_changed


class AdminService:
    def __init__(
        self,
        uow: Annotated[UnitOfWork, Depends()],
        lobby_service: Annotated[LobbyService, Depends()],
    ):
        self._uow = uow
        self._lobbies = lobby_service

    async def search_users(self, filters: AdminUserFilterSchema) -> PaginatedAdminUserSchema:
        async with self._uow as uow:
            return await uow.user_repo.search_users(filters)

    async def promote_user(self, user_id: int) -> None:
        async with self._uow as uow:
            if not await uow.user_repo.update_role(user_id, UserRole.ADMIN):
                raise NotFoundError(f"User {user_id} not found")

    async def delete_user(self, user_id: int, caller_id: int) -> None:
        """
        Hard-delete a non-admin user.

        Their unfinished lobbies go through the regular lobby removal; completed
        lobbies stay (owner becomes NULL, host name is snapshotted). Media no
        prompt uses is deleted with the files.
        """
        if user_id == caller_id:
            raise ForbiddenError("Admins cannot delete themselves")
        async with self._uow as uow:
            user = await uow.user_repo.select_user_for_auth(user_id=user_id)
            if user is None:
                raise NotFoundError(f"User {user_id} not found")
            if user.role == UserRole.ADMIN:
                raise ForbiddenError("Admins cannot be deleted")
            lobby_ids = await uow.lobby_repo.select_unfinished_lobby_ids_by_owner(user_id)
            for lobby_id in lobby_ids:
                await self._lobbies.remove_lobby(lobby_id)
            await uow.lobby_repo.snapshot_owner_username(user_id, user.username)
            storage_keys = await uow.media_asset_repo.delete_unattached_by_owner(user_id)
            await uow.user_repo.delete_user(user_id)
        for storage_key in storage_keys:
            (settings.media_root / storage_key).unlink(missing_ok=True)
        for lobby_id in lobby_ids:
            await self._lobbies.announce_lobby_removed(lobby_id)
        if lobby_ids:
            await notify_lobbies_changed()
