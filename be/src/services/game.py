from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends

from configs.constants import ANSWERING_TIME_SECONDS, BUZZING_TIME_SECONDS
from database import UnitOfWork
from enums.game import GamePhaseEnum, PlayerConnectionStatusEnum
from enums.lobby import LobbyStateEnum
from errors.request import BadRequestError, ForbiddenError, NotFoundError
from schemas.lobby.game_state import (
    GameCategoryState,
    GameHostState,
    GameLobbyState,
    GamePlayerState,
    GamePromptState,
)
from schemas.socket.events import (
    BanPlayerPayload,
    JudgeAnswerPayload,
    SelectPromptPayload,
    SelectStarterPayload,
    SubmitAnswerPayload,
    UnbanPlayerPayload,
)
from schemas.user.base import UserPublicSchema


class GameService:
    def __init__(self, uow: Annotated[UnitOfWork, Depends()]):
        self._uow = uow

    async def materialize_state(self, lobby_id: int) -> GameLobbyState:
        """
        Snapshot a lobby into Redis as the starting ``GameLobbyState``. Called
        on the ``created → waiting_start`` transition so the namespace is ready
        for players to connect.
        """
        async with self._uow as uow:
            return await self.materialize_state_in_uow(uow, lobby_id)

    @classmethod
    async def materialize_state_in_uow(
        cls,
        uow: UnitOfWork,
        lobby_id: int,
    ) -> GameLobbyState:
        """
        Same as :meth:`materialize_state` but reuses an already-open UoW so it
        can run inside another service's transaction (e.g. ``LobbyService`` on
        the ``created → waiting_start`` transition).
        """
        lobby = await uow.lobby_repo.select_lobby_with_prompts(lobby_id=lobby_id)
        if lobby is None:
            raise NotFoundError(f"Lobby {lobby_id} not found")
        if lobby.owner is None:
            raise BadRequestError("Lobby has no owner; cannot start a game")

        state = GameLobbyState(
            lobby_id=lobby.id,
            host=GameHostState(
                user_id=lobby.owner.id,
                username=lobby.owner.username,
            ),
            categories=[
                GameCategoryState(
                    category_id=category.id,
                    name=category.name,
                    prompts=[
                        GamePromptState(
                            prompt_id=prompt.id,
                            question=prompt.question,
                            answer=prompt.answer,
                            order=prompt.order or 0,
                        )
                        for prompt in category.prompts
                    ],
                )
                for category in lobby.prompt_categories
            ],
        )
        await uow.game_state_repo.save_state(state)
        return state

    async def connect_user(
        self,
        lobby_id: int,
        user: UserPublicSchema,
    ) -> GameLobbyState:
        async with self._uow as uow:
            state = await self._load_state(uow, lobby_id)
            if state.phase == GamePhaseEnum.FINISHED:
                raise ForbiddenError("Game has finished")

            if user.id == state.host.user_id:
                if state.host.connection_status == PlayerConnectionStatusEnum.CONNECTED:
                    raise ForbiddenError("Host is already connected from another device")
                state.host.connection_status = PlayerConnectionStatusEnum.CONNECTED
            else:
                player = _find_player(state, user.id)
                if player is None:
                    state.players.append(
                        GamePlayerState(
                            user_id=user.id,
                            username=user.username,
                            connection_status=PlayerConnectionStatusEnum.CONNECTED,
                        ),
                    )
                else:
                    if player.is_banned:
                        raise ForbiddenError("Player is banned from this lobby")
                    if player.connection_status == PlayerConnectionStatusEnum.CONNECTED:
                        raise ForbiddenError(
                            "Player is already connected from another device",
                        )
                    player.connection_status = PlayerConnectionStatusEnum.CONNECTED

            await uow.game_state_repo.save_state(state)
        return state

    async def disconnect_user(
        self,
        lobby_id: int,
        user_id: int,
    ) -> GameLobbyState | None:
        async with self._uow as uow:
            state = await uow.game_state_repo.get_state(lobby_id=lobby_id)
            if state is None:
                return None

            if user_id == state.host.user_id:
                state.host.connection_status = PlayerConnectionStatusEnum.DISCONNECTED
            else:
                player = _find_player(state, user_id)
                if player is None:
                    return state
                player.connection_status = PlayerConnectionStatusEnum.DISCONNECTED

            await uow.game_state_repo.save_state(state)
        return state

    async def start_game(self, lobby_id: int, user_id: int) -> GameLobbyState:
        async with self._uow as uow:
            state = await self._load_state(uow, lobby_id)
            _require_host(state, user_id)
            _require_phase(state, GamePhaseEnum.WAITING_FOR_PLAYERS)

            lobby = await uow.lobby_repo.select_lobby(lobby_id=lobby_id)
            if lobby is None:
                raise NotFoundError(f"Lobby {lobby_id} not found")
            if lobby.state != LobbyStateEnum.WAITING_START:
                raise BadRequestError(
                    "Lobby must be in WAITING_START to start the game",
                )

            connected_players = [
                p
                for p in state.players
                if p.connection_status == PlayerConnectionStatusEnum.CONNECTED and not p.is_banned
            ]
            if not connected_players:
                raise BadRequestError(
                    "At least one connected, non-banned player is required",
                )

            await uow.lobby_repo.update_lobby_state(
                lobby_id=lobby_id,
                state=LobbyStateEnum.IN_PROGRESS,
            )
            state.phase = GamePhaseEnum.HOST_SELECTING_STARTING_PLAYER
            await uow.game_state_repo.save_state(state)
        return state

    async def select_starter(
        self,
        lobby_id: int,
        user_id: int,
        payload: SelectStarterPayload,
    ) -> GameLobbyState:
        async with self._uow as uow:
            state = await self._load_state(uow, lobby_id)
            _require_host(state, user_id)
            _require_phase(state, GamePhaseEnum.HOST_SELECTING_STARTING_PLAYER)

            target = _find_player(state, payload.user_id)
            if target is None:
                raise BadRequestError(f"Player {payload.user_id} is not in this lobby")
            if target.is_banned:
                raise BadRequestError("Cannot select a banned player")
            if target.connection_status != PlayerConnectionStatusEnum.CONNECTED:
                raise BadRequestError("Selected player is not connected")

            _clear_selected_flags(state)
            target.is_selected = True
            state.selecting_player_id = target.user_id
            state.phase = GamePhaseEnum.PLAYER_SELECTING_PROMPT

            await uow.game_state_repo.save_state(state)
        return state

    async def select_prompt(
        self,
        lobby_id: int,
        user_id: int,
        payload: SelectPromptPayload,
    ) -> GameLobbyState:
        async with self._uow as uow:
            state = await self._load_state(uow, lobby_id)
            _require_phase(state, GamePhaseEnum.PLAYER_SELECTING_PROMPT)
            if state.selecting_player_id != user_id:
                raise ForbiddenError("Only the selecting player may pick a prompt")

            prompt = _find_prompt(state, payload.prompt_id)
            if prompt is None:
                raise BadRequestError(
                    f"Prompt {payload.prompt_id} is not in this lobby",
                )
            if prompt.is_selected:
                raise BadRequestError("Prompt has already been used")

            prompt.is_selected = True
            state.current_prompt_id = prompt.prompt_id
            state.answering_player_id = state.selecting_player_id
            state.attempted_player_ids = []
            state.last_submitted_answer = None
            state.phase = GamePhaseEnum.PLAYER_ANSWERING
            state.timer_deadline = _deadline(ANSWERING_TIME_SECONDS)

            await uow.game_state_repo.save_state(state)
        return state

    async def submit_answer(
        self,
        lobby_id: int,
        user_id: int,
        payload: SubmitAnswerPayload,
    ) -> GameLobbyState:
        async with self._uow as uow:
            state = await self._load_state(uow, lobby_id)
            _require_phase(state, GamePhaseEnum.PLAYER_ANSWERING)
            if state.answering_player_id != user_id:
                raise ForbiddenError("Only the answering player may submit an answer")

            state.last_submitted_answer = payload.text
            state.phase = GamePhaseEnum.HOST_JUDGING_ANSWER
            state.timer_deadline = None

            await uow.game_state_repo.save_state(state)
        return state

    async def judge_answer(
        self,
        lobby_id: int,
        user_id: int,
        payload: JudgeAnswerPayload,
    ) -> GameLobbyState:
        async with self._uow as uow:
            state = await self._load_state(uow, lobby_id)
            _require_host(state, user_id)
            _require_phase(state, GamePhaseEnum.HOST_JUDGING_ANSWER)
            if state.current_prompt_id is None or state.answering_player_id is None:
                raise BadRequestError("No prompt is currently being judged")

            prompt = _find_prompt(state, state.current_prompt_id)
            answerer = _find_player(state, state.answering_player_id)
            if prompt is None or answerer is None:
                raise BadRequestError("Active prompt or player is missing from state")

            if payload.correct:
                answerer.score += prompt.score_value
                _clear_selected_flags(state)
                answerer.is_selected = True
                state.selecting_player_id = answerer.user_id
                state.answering_player_id = None
                state.current_prompt_id = None
                state.attempted_player_ids = []
                state.last_submitted_answer = None
                state.phase = GamePhaseEnum.PLAYER_SELECTING_PROMPT
                state.timer_deadline = None
                await self._check_end_of_game(uow, state)
            else:
                answerer.score -= prompt.score_value
                answerer.is_selected = False
                state.attempted_player_ids.append(answerer.user_id)
                state.answering_player_id = None
                state.last_submitted_answer = None
                if _eligible_buzzers(state):
                    state.phase = GamePhaseEnum.BUZZ_OPEN
                    state.timer_deadline = _deadline(BUZZING_TIME_SECONDS)
                else:
                    _resolve_prompt_no_score(state)

            await uow.game_state_repo.save_state(state)
        return state

    async def buzz(self, lobby_id: int, user_id: int) -> GameLobbyState:
        async with self._uow as uow:
            state = await self._load_state(uow, lobby_id)
            _require_phase(state, GamePhaseEnum.BUZZ_OPEN)

            player = _find_player(state, user_id)
            if player is None:
                raise ForbiddenError("Only lobby players may buzz")
            if player.is_banned:
                raise ForbiddenError("Banned players may not buzz")
            if player.connection_status != PlayerConnectionStatusEnum.CONNECTED:
                raise ForbiddenError("Disconnected players may not buzz")
            if user_id in state.attempted_player_ids:
                raise ForbiddenError("You already attempted this prompt")

            _clear_selected_flags(state)
            player.is_selected = True
            state.answering_player_id = user_id
            state.phase = GamePhaseEnum.PLAYER_ANSWERING
            state.timer_deadline = _deadline(ANSWERING_TIME_SECONDS)

            await uow.game_state_repo.save_state(state)
        return state

    async def ban_player(
        self,
        lobby_id: int,
        user_id: int,
        payload: BanPlayerPayload,
    ) -> GameLobbyState:
        async with self._uow as uow:
            state = await self._load_state(uow, lobby_id)
            _require_host(state, user_id)

            target = _find_player(state, payload.user_id)
            if target is None:
                raise BadRequestError(f"Player {payload.user_id} is not in this lobby")

            target.is_banned = True
            target.connection_status = PlayerConnectionStatusEnum.DISCONNECTED

            await uow.game_state_repo.save_state(state)
        return state

    async def unban_player(
        self,
        lobby_id: int,
        user_id: int,
        payload: UnbanPlayerPayload,
    ) -> GameLobbyState:
        async with self._uow as uow:
            state = await self._load_state(uow, lobby_id)
            _require_host(state, user_id)

            target = _find_player(state, payload.user_id)
            if target is None:
                raise BadRequestError(f"Player {payload.user_id} is not in this lobby")

            target.is_banned = False

            await uow.game_state_repo.save_state(state)
        return state

    async def expire_timer(self, lobby_id: int) -> GameLobbyState | None:
        """
        Apply the timer-expiry rules for whichever phase is currently active.
        Returns the new state for broadcast, or ``None`` if no state exists or
        the deadline is stale (a newer timer was armed).
        """
        async with self._uow as uow:
            state = await uow.game_state_repo.get_state(lobby_id=lobby_id)
            if state is None or state.timer_deadline is None:
                return None
            if state.timer_deadline > datetime.now(UTC):
                return None

            if state.phase == GamePhaseEnum.PLAYER_ANSWERING:
                if state.answering_player_id is not None:
                    state.attempted_player_ids.append(state.answering_player_id)
                    expired = _find_player(state, state.answering_player_id)
                    if expired is not None:
                        expired.is_selected = False
                state.answering_player_id = None
                state.last_submitted_answer = None
                if _eligible_buzzers(state):
                    state.phase = GamePhaseEnum.BUZZ_OPEN
                    state.timer_deadline = _deadline(BUZZING_TIME_SECONDS)
                else:
                    _resolve_prompt_no_score(state)
            elif state.phase == GamePhaseEnum.BUZZ_OPEN:
                _resolve_prompt_no_score(state)
            else:
                return None

            await uow.game_state_repo.save_state(state)
        return state

    @classmethod
    async def _load_state(
        cls,
        uow: UnitOfWork,
        lobby_id: int,
    ) -> GameLobbyState:
        state = await uow.game_state_repo.get_state(lobby_id=lobby_id)
        if state is None:
            raise NotFoundError(f"Game state for lobby {lobby_id} not found")
        return state

    @classmethod
    async def _check_end_of_game(
        cls,
        uow: UnitOfWork,
        state: GameLobbyState,
    ) -> None:
        all_used = all(
            prompt.is_selected for category in state.categories for prompt in category.prompts
        )
        if not all_used:
            return
        state.phase = GamePhaseEnum.FINISHED
        state.selecting_player_id = None
        state.timer_deadline = None
        _clear_selected_flags(state)
        await uow.lobby_repo.update_lobby_state(
            lobby_id=state.lobby_id,
            state=LobbyStateEnum.COMPLETED,
        )


def _find_player(state: GameLobbyState, user_id: int) -> GamePlayerState | None:
    return next((p for p in state.players if p.user_id == user_id), None)


def _find_prompt(state: GameLobbyState, prompt_id: int) -> GamePromptState | None:
    for category in state.categories:
        for prompt in category.prompts:
            if prompt.prompt_id == prompt_id:
                return prompt
    return None


def _clear_selected_flags(state: GameLobbyState) -> None:
    for player in state.players:
        player.is_selected = False


def _eligible_buzzers(state: GameLobbyState) -> list[GamePlayerState]:
    return [
        p
        for p in state.players
        if p.connection_status == PlayerConnectionStatusEnum.CONNECTED
        and not p.is_banned
        and p.user_id not in state.attempted_player_ids
    ]


def _resolve_prompt_no_score(state: GameLobbyState) -> None:
    """
    Close out the current prompt with no score change. Selecting role stays
    with whoever picked the prompt (``selecting_player_id`` is untouched).
    """
    state.current_prompt_id = None
    state.answering_player_id = None
    state.attempted_player_ids = []
    state.last_submitted_answer = None
    state.timer_deadline = None
    state.phase = GamePhaseEnum.PLAYER_SELECTING_PROMPT
    _clear_selected_flags(state)
    if state.selecting_player_id is not None:
        selector = _find_player(state, state.selecting_player_id)
        if selector is not None:
            selector.is_selected = True


def _require_host(state: GameLobbyState, user_id: int) -> None:
    if user_id != state.host.user_id:
        raise ForbiddenError("Only the host may perform this action")


def _require_phase(state: GameLobbyState, *phases: GamePhaseEnum) -> None:
    if state.phase not in phases:
        raise BadRequestError(
            f"Action not allowed during phase {state.phase.value}",
        )


def _deadline(seconds: int) -> datetime:
    return datetime.now(UTC) + timedelta(seconds=seconds)
