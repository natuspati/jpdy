from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends

from configs.constants import (
    ANSWER_REVEAL_TIME_SECONDS,
    ANSWERING_TIME_SECONDS,
    BUZZING_TIME_SECONDS,
)
from database import UnitOfWork
from enums.game import GamePhaseEnum, GameResolutionEnum, PlayerConnectionStatusEnum
from enums.lobby import LobbyStateEnum
from errors.request import BadRequestError, ForbiddenError, NotFoundError
from schemas.lobby.game_state import (
    GameCategoryState,
    GameHostState,
    GameLobbyState,
    GamePlayerState,
    GamePromptState,
)
from schemas.media import MediaReferenceSchema
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
                            question_type=prompt.question_type,
                            answer_type=prompt.answer_type,
                            question_media=(
                                MediaReferenceSchema.from_asset(prompt.question_media_asset)
                                if prompt.question_media_asset is not None
                                else None
                            ),
                            answer_media=(
                                MediaReferenceSchema.from_asset(prompt.answer_media_asset)
                                if prompt.answer_media_asset is not None
                                else None
                            ),
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
                # Socket handlers replace an older live socket for this user.
                # Treat the persisted flag as recoverable so users can return
                # after a transport drop or backend restart.
                state.host.connection_status = PlayerConnectionStatusEnum.CONNECTED
            else:
                player = _find_player(state, user.id)
                participant = await uow.lobby_repo.select_participant(
                    lobby_id=lobby_id,
                    user_id=user.id,
                )
                if participant is not None and participant.is_banned:
                    raise ForbiddenError("Player is banned from this lobby")
                if player is None:
                    lobby = await uow.lobby_repo.select_lobby(lobby_id=lobby_id)
                    if lobby is None:
                        raise NotFoundError(f"Lobby {lobby_id} not found")
                    if lobby.state != LobbyStateEnum.WAITING_START:
                        raise ForbiddenError(
                            "Lobby roster is locked after the game has started",
                        )
                    await uow.lobby_repo.ensure_participant(lobby_id=lobby_id, user=user)
                    state.players.append(
                        GamePlayerState(
                            user_id=user.id,
                            username=user.username,
                            connection_status=PlayerConnectionStatusEnum.CONNECTED,
                        ),
                    )
                else:
                    if player.is_banned:
                        if participant is None:
                            await uow.lobby_repo.ensure_participant(lobby_id=lobby_id, user=user)
                        await uow.lobby_repo.update_participant_ban(
                            lobby_id=lobby_id,
                            user_id=user.id,
                            is_banned=True,
                        )
                        raise ForbiddenError("Player is banned from this lobby")
                    if participant is None:
                        await uow.lobby_repo.ensure_participant(lobby_id=lobby_id, user=user)
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
            _clear_selected_flags(state)
            answerer = _find_player(state, state.answering_player_id)
            if answerer is not None:
                answerer.is_selected = True
            _clear_resolution(state)
            state.phase = GamePhaseEnum.PLAYER_ANSWERING
            state.timer_deadline = _deadline(ANSWERING_TIME_SECONDS)

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
            _require_phase(state, GamePhaseEnum.PLAYER_ANSWERING)
            if state.current_prompt_id is None or state.answering_player_id is None:
                raise BadRequestError("No prompt is currently being judged")
            if state.timer_deadline is None or state.timer_deadline <= datetime.now(UTC):
                raise BadRequestError("Answer time has expired")

            prompt = _find_prompt(state, state.current_prompt_id)
            answerer = _find_player(state, state.answering_player_id)
            if prompt is None or answerer is None:
                raise BadRequestError("Active prompt or player is missing from state")

            if payload.correct:
                answerer.score += prompt.score_value
                _clear_selected_flags(state)
                state.selecting_player_id = answerer.user_id
                state.answering_player_id = None
                _enter_answer_reveal(state, GameResolutionEnum.CORRECT)
            else:
                answerer.score -= prompt.score_value
                answerer.is_selected = False
                if answerer.user_id not in state.attempted_player_ids:
                    state.attempted_player_ids.append(answerer.user_id)
                state.answering_player_id = None
                if _eligible_buzzers(state):
                    state.phase = GamePhaseEnum.BUZZ_OPEN
                    state.timer_deadline = _deadline(BUZZING_TIME_SECONDS)
                else:
                    _enter_answer_reveal(state, GameResolutionEnum.UNANSWERED)

            await uow.game_state_repo.save_state(state)
        return state

    async def buzz(
        self,
        lobby_id: int,
        user_id: int,
    ) -> GameLobbyState:
        async with self._uow as uow:
            state = await self._load_state(uow, lobby_id)
            _require_phase(state, GamePhaseEnum.BUZZ_OPEN)
            if state.timer_deadline is None or state.timer_deadline <= datetime.now(UTC):
                raise BadRequestError("Buzz time has expired")

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
            participant = await uow.lobby_repo.select_participant(
                lobby_id=lobby_id,
                user_id=target.user_id,
            )
            if participant is None:
                await uow.lobby_repo.ensure_participant(
                    lobby_id=lobby_id,
                    user=UserPublicSchema(id=target.user_id, username=target.username),
                )
            await uow.lobby_repo.update_participant_ban(
                lobby_id=lobby_id,
                user_id=target.user_id,
                is_banned=True,
            )
            _recover_from_banned_player(state, target.user_id)

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
            participant = await uow.lobby_repo.select_participant(
                lobby_id=lobby_id,
                user_id=target.user_id,
            )
            if participant is None:
                await uow.lobby_repo.ensure_participant(
                    lobby_id=lobby_id,
                    user=UserPublicSchema(id=target.user_id, username=target.username),
                )
            await uow.lobby_repo.update_participant_ban(
                lobby_id=lobby_id,
                user_id=target.user_id,
                is_banned=False,
            )

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
                    if state.answering_player_id not in state.attempted_player_ids:
                        state.attempted_player_ids.append(state.answering_player_id)
                    expired = _find_player(state, state.answering_player_id)
                    if expired is not None:
                        expired.is_selected = False
                state.answering_player_id = None
                if _eligible_buzzers(state):
                    state.phase = GamePhaseEnum.BUZZ_OPEN
                    state.timer_deadline = _deadline(BUZZING_TIME_SECONDS)
                else:
                    _enter_answer_reveal(state, GameResolutionEnum.EXPIRED)
            elif state.phase == GamePhaseEnum.BUZZ_OPEN:
                _enter_answer_reveal(state, GameResolutionEnum.EXPIRED)
            elif state.phase == GamePhaseEnum.ANSWER_REVEAL:
                await self._advance_after_reveal(uow, state)
            else:
                return None

            await uow.game_state_repo.save_state(state)
        return state

    async def issue_sound_cue(
        self,
        lobby_id: int,
        cue: GameSoundCueName,
    ) -> GameSoundCuePayload:
        """
        Reserve a monotonically increasing presentation-only sound cue id.
        Gameplay has already changed when this runs; failures cannot roll back
        timers, phases, scores, or permissions.
        """
        async with self._uow as uow:
            state = await self._load_state(uow, lobby_id)
            state.sound_cue_id += 1
            await uow.game_state_repo.save_state(state)
        return GameSoundCuePayload(cue_id=state.sound_cue_id, cue=cue)

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
    async def _advance_after_reveal(
        cls,
        uow: UnitOfWork,
        state: GameLobbyState,
    ) -> None:
        state.current_prompt_id = None
        state.answering_player_id = None
        state.attempted_player_ids = []
        state.timer_deadline = None
        _clear_resolution(state)
        _clear_selected_flags(state)

        all_used = all(
            prompt.is_selected for category in state.categories for prompt in category.prompts
        )
        if not all_used:
            selector = _find_player(state, state.selecting_player_id)
            if _is_eligible_player(selector):
                state.phase = GamePhaseEnum.PLAYER_SELECTING_PROMPT
                selector.is_selected = True
            else:
                _enter_host_player_selection(state)
            return

        state.phase = GamePhaseEnum.FINISHED
        state.selecting_player_id = None
        await uow.lobby_repo.snapshot_final_results(
            lobby_id=state.lobby_id,
            players=[
                (player.user_id, player.username, player.score, player.is_banned)
                for player in state.players
            ],
        )
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


def _is_eligible_player(player: GamePlayerState | None) -> bool:
    return (
        player is not None
        and not player.is_banned
        and player.connection_status == PlayerConnectionStatusEnum.CONNECTED
    )


def _enter_host_player_selection(state: GameLobbyState) -> None:
    _clear_selected_flags(state)
    state.selecting_player_id = None
    state.answering_player_id = None
    state.timer_deadline = None
    state.phase = GamePhaseEnum.HOST_SELECTING_STARTING_PLAYER


def _recover_from_banned_player(state: GameLobbyState, user_id: int) -> None:
    """
    Remove a banned player from active ownership without discarding a spent
    prompt. An interrupted answer becomes a normal unanswered reveal.
    """
    is_selector = state.selecting_player_id == user_id
    is_answerer = state.answering_player_id == user_id

    if state.phase == GamePhaseEnum.PLAYER_SELECTING_PROMPT and is_selector:
        _enter_host_player_selection(state)
        return

    if state.phase == GamePhaseEnum.PLAYER_ANSWERING and is_answerer:
        state.selecting_player_id = None
        _clear_selected_flags(state)
        _enter_answer_reveal(state, GameResolutionEnum.UNANSWERED)
        return

    if is_selector:
        state.selecting_player_id = None
        banned_player = _find_player(state, user_id)
        if banned_player is not None:
            banned_player.is_selected = False

    if state.phase == GamePhaseEnum.BUZZ_OPEN and not _eligible_buzzers(state):
        _enter_answer_reveal(state, GameResolutionEnum.UNANSWERED)


def _enter_answer_reveal(
    state: GameLobbyState,
    resolution: GameResolutionEnum,
) -> None:
    """Make a resolved clue public for the server-authoritative reveal window."""
    if state.current_prompt_id is None:
        raise BadRequestError("No active prompt to reveal")
    prompt = _find_prompt(state, state.current_prompt_id)
    if prompt is None:
        raise BadRequestError("Active prompt is missing from state")

    state.answering_player_id = None
    _clear_selected_flags(state)
    state.phase = GamePhaseEnum.ANSWER_REVEAL
    state.timer_deadline = _deadline(ANSWER_REVEAL_TIME_SECONDS)
    state.resolved_prompt_id = prompt.prompt_id
    state.resolved_answer = prompt.answer
    state.resolved_answer_type = prompt.answer_type
    state.resolved_answer_media = prompt.answer_media
    state.resolution = resolution


def _clear_resolution(state: GameLobbyState) -> None:
    state.resolved_prompt_id = None
    state.resolved_answer = None
    state.resolved_answer_type = None
    state.resolved_answer_media = None
    state.resolution = None


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
