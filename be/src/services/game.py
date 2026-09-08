from datetime import datetime
from functools import partial
from typing import Annotated

from fastapi import Depends

from database import UnitOfWork
from errors.request import NotFoundError
from schemas.lobby.game_state import GameLobbyState
from schemas.socket.events import (
    BanPlayerPayload,
    GameSoundCueName,
    GameSoundCuePayload,
    JudgeAnswerPayload,
    SelectPromptPayload,
    SelectStarterPayload,
    UnbanPlayerPayload,
)
from schemas.user.base import UserPublicSchema
from services.game_command_executor import GameCommandExecutor
from services.game_projection import GameProjectionService
from services.game_state_machine import GameStateMachine


class GameService:
    """Application-facing façade for Redis live-game commands."""

    def __init__(self, uow: Annotated[UnitOfWork, Depends()]):
        self._executor = GameCommandExecutor(uow)
        self._projections = GameProjectionService(uow)
        self._state_machine = GameStateMachine()

    async def connect_user(
        self,
        lobby_id: int,
        user: UserPublicSchema,
        command_id: str | None = None,
    ) -> GameLobbyState:
        state = await self._executor.execute(
            lobby_id,
            command_id,
            "connect_user",
            partial(self._state_machine.connect_user, user_id=user.id, username=user.username),
        )
        assert state is not None
        if user.id != state.host.user_id:
            await self._projections.project_connected_player(state, user)
        return state

    async def disconnect_user(
        self,
        lobby_id: int,
        user_id: int,
        command_id: str | None = None,
    ) -> GameLobbyState | None:
        try:
            return await self._executor.execute(
                lobby_id,
                command_id,
                "disconnect_user",
                partial(self._state_machine.disconnect_user, user_id=user_id),
            )
        except NotFoundError:
            return None

    async def start_game(
        self,
        lobby_id: int,
        user_id: int,
        command_id: str | None = None,
    ) -> GameLobbyState:
        state = await self._executor.execute(
            lobby_id,
            command_id,
            "start_game",
            partial(self._state_machine.start_game, user_id=user_id),
        )
        assert state is not None
        await self._projections.project_game_started(state)
        return state

    async def select_starter(
        self,
        lobby_id: int,
        user_id: int,
        payload: SelectStarterPayload,
        command_id: str | None = None,
    ) -> GameLobbyState:
        state = await self._executor.execute(
            lobby_id,
            command_id,
            "select_starter",
            partial(
                self._state_machine.select_starter,
                user_id=user_id,
                target_user_id=payload.user_id,
            ),
        )
        assert state is not None
        return state

    async def select_prompt(
        self,
        lobby_id: int,
        user_id: int,
        payload: SelectPromptPayload,
        command_id: str | None = None,
    ) -> GameLobbyState:
        state = await self._executor.execute(
            lobby_id,
            command_id,
            "select_prompt",
            partial(
                self._state_machine.select_prompt,
                user_id=user_id,
                prompt_id=payload.prompt_id,
            ),
        )
        assert state is not None
        return state

    async def judge_answer(
        self,
        lobby_id: int,
        user_id: int,
        payload: JudgeAnswerPayload,
        command_id: str | None = None,
    ) -> GameLobbyState:
        state = await self._executor.execute(
            lobby_id,
            command_id,
            "judge_answer",
            partial(self._state_machine.judge_answer, user_id=user_id, correct=payload.correct),
        )
        assert state is not None
        return state

    async def buzz(
        self,
        lobby_id: int,
        user_id: int,
        command_id: str | None = None,
    ) -> GameLobbyState:
        state = await self._executor.execute(
            lobby_id,
            command_id,
            "buzz",
            partial(self._state_machine.buzz, user_id=user_id),
        )
        assert state is not None
        return state

    async def advance_answer_reveal(
        self,
        lobby_id: int,
        user_id: int,
        command_id: str | None = None,
    ) -> GameLobbyState:
        state = await self._executor.execute(
            lobby_id,
            command_id,
            "advance_answer_reveal",
            partial(self._state_machine.advance_answer_reveal, user_id=user_id),
        )
        assert state is not None
        await self._projections.project_completion(state)
        return state

    async def ban_player(
        self,
        lobby_id: int,
        user_id: int,
        payload: BanPlayerPayload,
        command_id: str | None = None,
    ) -> GameLobbyState:
        state = await self._executor.execute(
            lobby_id,
            command_id,
            "ban_player",
            partial(
                self._state_machine.ban_player,
                user_id=user_id,
                target_user_id=payload.user_id,
            ),
        )
        assert state is not None
        await self._projections.project_participant(state, payload.user_id)
        return state

    async def unban_player(
        self,
        lobby_id: int,
        user_id: int,
        payload: UnbanPlayerPayload,
        command_id: str | None = None,
    ) -> GameLobbyState:
        state = await self._executor.execute(
            lobby_id,
            command_id,
            "unban_player",
            partial(
                self._state_machine.unban_player,
                user_id=user_id,
                target_user_id=payload.user_id,
            ),
        )
        assert state is not None
        await self._projections.project_participant(state, payload.user_id)
        return state

    async def expire_timer(
        self,
        lobby_id: int,
        expected_revision: int | None = None,
        expected_deadline: datetime | None = None,
        command_id: str | None = None,
    ) -> GameLobbyState | None:
        try:
            state = await self._executor.execute(
                lobby_id,
                command_id,
                "expire_timer",
                partial(
                    self._state_machine.expire_timer,
                    expected_revision=expected_revision,
                    expected_deadline=expected_deadline,
                ),
            )
        except NotFoundError:
            return None
        if state is not None:
            await self._projections.project_completion(state)
        return state

    async def issue_sound_cue(
        self,
        lobby_id: int,
        cue: GameSoundCueName,
        command_id: str | None = None,
    ) -> GameSoundCuePayload:
        state = await self._executor.execute(
            lobby_id,
            command_id,
            "issue_sound_cue",
            partial(self._state_machine.issue_sound_cue, cue=cue.value),
        )
        assert state is not None
        return GameSoundCuePayload(cue_id=state.sound_cue_id, cue=cue)
