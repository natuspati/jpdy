from redis.asyncio import Redis

from schemas.lobby.game_state import GameLobbyState


class GameStateRepo:
    def __init__(self, redis: Redis):
        self._redis = redis

    async def get_state(self, lobby_id: int) -> GameLobbyState | None:
        """
        Read the ``GameLobbyState`` stored under ``lobby:{lobby_id}``.

        :param lobby_id: lobby primary key
        :return: deserialized game state, or ``None`` if the key is missing
        """
        raw = await self._redis.get(GameLobbyState.redis_key(lobby_id))
        if raw is None:
            return None
        return GameLobbyState.model_validate_json(raw)

    async def save_state(self, state: GameLobbyState) -> None:
        """
        Persist ``state`` under its ``lobby:{lobby_id}`` key, overwriting any
        prior value. The whole blob is replaced; partial updates are not
        supported on purpose so callers always work with a complete snapshot.
        """
        await self._redis.set(state.key, state.model_dump_json())

    async def delete_state(self, lobby_id: int) -> None:
        await self._redis.delete(GameLobbyState.redis_key(lobby_id))
