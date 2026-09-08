from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import uuid4

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
from repos.game_state import GameStateConflictError, GameStateMissingError
from schemas.lobby.game_state import GameLobbyState, GamePlayerState, GamePromptState
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
from utils.game_state import GameCommandOutcome


class GameService:
    """Redis-authoritative live-game command service."""

    def __init__(self, uow: Annotated[UnitOfWork, Depends()]):
        self._uow = uow

    async def connect_user(
        self,
        lobby_id: int,
        user: UserPublicSchema,
        command_id: str | None = None,
    ) -> GameLobbyState:
        def transition(state: GameLobbyState) -> GameCommandOutcome:
            if state.phase == GamePhaseEnum.FINISHED:
                raise ForbiddenError("Game has finished")
            if user.id == state.host.user_id:
                state.host.connection_status = PlayerConnectionStatusEnum.CONNECTED
            else:
                player = _find_player(state, user.id)
                if player is None:
                    if state.phase != GamePhaseEnum.WAITING_FOR_PLAYERS:
                        raise ForbiddenError("Lobby roster is locked after the game has started")
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
                    player.connection_status = PlayerConnectionStatusEnum.CONNECTED
            return GameCommandOutcome(state=state, result=state, reason="user_connected")

        state = await self._execute(lobby_id, command_id, "connect_user", transition)
        if user.id != state.host.user_id:
            async with self._uow as uow:
                await uow.lobby_repo.ensure_participant(lobby_id=lobby_id, user=user)
        return state

    async def disconnect_user(
        self,
        lobby_id: int,
        user_id: int,
        command_id: str | None = None,
    ) -> GameLobbyState | None:
        def transition(state: GameLobbyState) -> GameCommandOutcome:
            if user_id == state.host.user_id:
                state.host.connection_status = PlayerConnectionStatusEnum.DISCONNECTED
            else:
                player = _find_player(state, user_id)
                if player is None:
                    return GameCommandOutcome(state=None, result=state, reason="unknown_disconnect")
                player.connection_status = PlayerConnectionStatusEnum.DISCONNECTED
            return GameCommandOutcome(state=state, result=state, reason="user_disconnected")

        try:
            return await self._execute(lobby_id, command_id, "disconnect_user", transition)
        except NotFoundError:
            return None

    async def start_game(
        self,
        lobby_id: int,
        user_id: int,
        command_id: str | None = None,
    ) -> GameLobbyState:
        def transition(state: GameLobbyState) -> GameCommandOutcome:
            _require_host(state, user_id)
            _require_phase(state, GamePhaseEnum.WAITING_FOR_PLAYERS)
            if not any(_is_eligible_player(player) for player in state.players):
                raise BadRequestError("At least one connected, non-banned player is required")
            state.phase = GamePhaseEnum.HOST_SELECTING_STARTING_PLAYER
            return GameCommandOutcome(state=state, result=state, reason="game_started")

        state = await self._execute(lobby_id, command_id, "start_game", transition)
        async with self._uow as uow:
            await uow.lobby_repo.update_lobby_state(lobby_id, LobbyStateEnum.IN_PROGRESS)
        return state

    async def select_starter(
        self,
        lobby_id: int,
        user_id: int,
        payload: SelectStarterPayload,
        command_id: str | None = None,
    ) -> GameLobbyState:
        def transition(state: GameLobbyState) -> GameCommandOutcome:
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
            return GameCommandOutcome(state=state, result=state, reason="starter_selected")

        return await self._execute(lobby_id, command_id, "select_starter", transition)

    async def select_prompt(
        self,
        lobby_id: int,
        user_id: int,
        payload: SelectPromptPayload,
        command_id: str | None = None,
    ) -> GameLobbyState:
        def transition(state: GameLobbyState) -> GameCommandOutcome:
            _require_phase(state, GamePhaseEnum.PLAYER_SELECTING_PROMPT)
            if state.selecting_player_id != user_id:
                raise ForbiddenError("Only the selecting player may pick a prompt")
            prompt = _find_prompt(state, payload.prompt_id)
            if prompt is None:
                raise BadRequestError(f"Prompt {payload.prompt_id} is not in this lobby")
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
            return GameCommandOutcome(state=state, result=state, reason="prompt_selected")

        return await self._execute(lobby_id, command_id, "select_prompt", transition)

    async def judge_answer(
        self,
        lobby_id: int,
        user_id: int,
        payload: JudgeAnswerPayload,
        command_id: str | None = None,
    ) -> GameLobbyState:
        def transition(state: GameLobbyState) -> GameCommandOutcome:
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
            return GameCommandOutcome(state=state, result=state, reason="answer_judged")

        return await self._execute(lobby_id, command_id, "judge_answer", transition)

    async def buzz(
        self,
        lobby_id: int,
        user_id: int,
        command_id: str | None = None,
    ) -> GameLobbyState:
        def transition(state: GameLobbyState) -> GameCommandOutcome:
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
            return GameCommandOutcome(state=state, result=state, reason="buzz_accepted")

        return await self._execute(lobby_id, command_id, "buzz", transition)

    async def advance_answer_reveal(
        self,
        lobby_id: int,
        user_id: int,
        command_id: str | None = None,
    ) -> GameLobbyState:
        def transition(state: GameLobbyState) -> GameCommandOutcome:
            _require_host(state, user_id)
            _require_phase(state, GamePhaseEnum.ANSWER_REVEAL)
            _advance_after_reveal(state)
            return GameCommandOutcome(state=state, result=state, reason="answer_reveal_advanced")

        state = await self._execute(lobby_id, command_id, "advance_answer_reveal", transition)
        await self._project_completion(state)
        return state

    async def ban_player(
        self,
        lobby_id: int,
        user_id: int,
        payload: BanPlayerPayload,
        command_id: str | None = None,
    ) -> GameLobbyState:
        def transition(state: GameLobbyState) -> GameCommandOutcome:
            _require_host(state, user_id)
            target = _find_player(state, payload.user_id)
            if target is None:
                raise BadRequestError(f"Player {payload.user_id} is not in this lobby")
            target.is_banned = True
            target.connection_status = PlayerConnectionStatusEnum.DISCONNECTED
            _recover_from_banned_player(state, target.user_id)
            return GameCommandOutcome(state=state, result=state, reason="player_banned")

        state = await self._execute(lobby_id, command_id, "ban_player", transition)
        await self._project_participant(state, payload.user_id)
        return state

    async def unban_player(
        self,
        lobby_id: int,
        user_id: int,
        payload: UnbanPlayerPayload,
        command_id: str | None = None,
    ) -> GameLobbyState:
        def transition(state: GameLobbyState) -> GameCommandOutcome:
            _require_host(state, user_id)
            target = _find_player(state, payload.user_id)
            if target is None:
                raise BadRequestError(f"Player {payload.user_id} is not in this lobby")
            target.is_banned = False
            return GameCommandOutcome(state=state, result=state, reason="player_unbanned")

        state = await self._execute(lobby_id, command_id, "unban_player", transition)
        await self._project_participant(state, payload.user_id)
        return state

    async def expire_timer(
        self,
        lobby_id: int,
        expected_revision: int | None = None,
        expected_deadline: datetime | None = None,
        command_id: str | None = None,
    ) -> GameLobbyState | None:
        def transition(state: GameLobbyState) -> GameCommandOutcome:
            if state.timer_deadline is None:
                return GameCommandOutcome(state=None, result=None, reason="no_timer")
            if expected_revision is not None and state.timer_revision != expected_revision:
                return GameCommandOutcome(state=None, result=None, reason="stale_timer_revision")
            if expected_deadline is not None and state.timer_deadline != expected_deadline:
                return GameCommandOutcome(state=None, result=None, reason="stale_timer_deadline")
            if state.timer_deadline > datetime.now(UTC):
                return GameCommandOutcome(state=None, result=None, reason="timer_not_due")
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
                _advance_after_reveal(state)
            else:
                return GameCommandOutcome(state=None, result=None, reason="timer_phase_not_timed")
            return GameCommandOutcome(state=state, result=state, reason="timer_expired")

        try:
            state = await self._execute(lobby_id, command_id, "expire_timer", transition)
        except NotFoundError:
            return None
        if state is not None:
            await self._project_completion(state)
        return state

    async def issue_sound_cue(
        self,
        lobby_id: int,
        cue: GameSoundCueName,
        command_id: str | None = None,
    ) -> GameSoundCuePayload:
        def transition(state: GameLobbyState) -> GameCommandOutcome:
            state.sound_cue_id += 1
            return GameCommandOutcome(state=state, result=state, reason=f"sound_cue:{cue.value}")

        state = await self._execute(lobby_id, command_id, "issue_sound_cue", transition)
        return GameSoundCuePayload(cue_id=state.sound_cue_id, cue=cue)

    async def _execute(
        self,
        lobby_id: int,
        command_id: str | None,
        command_name: str,
        transition: Callable[[GameLobbyState], GameCommandOutcome],
    ) -> GameLobbyState | None:
        try:
            async with self._uow as uow:
                return await uow.game_state_repo.execute(
                    lobby_id=lobby_id,
                    command_id=command_id or uuid4().hex,
                    command_name=command_name,
                    transition=transition,
                )
        except GameStateMissingError as error:
            raise NotFoundError(str(error)) from error
        except GameStateConflictError as error:
            raise BadRequestError("Game is busy; retry the command") from error

    async def _project_participant(self, state: GameLobbyState, user_id: int) -> None:
        player = _find_player(state, user_id)
        if player is None:
            return
        async with self._uow as uow:
            await uow.lobby_repo.ensure_participant(
                lobby_id=state.lobby_id,
                user=UserPublicSchema(id=player.user_id, username=player.username),
            )
            await uow.lobby_repo.update_participant_ban(
                lobby_id=state.lobby_id,
                user_id=player.user_id,
                is_banned=player.is_banned,
            )

    async def _project_completion(self, state: GameLobbyState) -> None:
        if state.phase != GamePhaseEnum.FINISHED:
            return
        async with self._uow as uow:
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


def _find_player(state: GameLobbyState, user_id: int | None) -> GamePlayerState | None:
    if user_id is None:
        return None
    return next((player for player in state.players if player.user_id == user_id), None)


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
        player
        for player in state.players
        if player.connection_status == PlayerConnectionStatusEnum.CONNECTED
        and not player.is_banned
        and player.user_id not in state.attempted_player_ids
    ]


def _is_eligible_player(player: GamePlayerState | None) -> bool:
    return (
        player is not None
        and not player.is_banned
        and player.connection_status == PlayerConnectionStatusEnum.CONNECTED
    )


def _advance_after_reveal(state: GameLobbyState) -> None:
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


def _enter_host_player_selection(state: GameLobbyState) -> None:
    _clear_selected_flags(state)
    state.selecting_player_id = None
    state.answering_player_id = None
    state.timer_deadline = None
    state.phase = GamePhaseEnum.HOST_SELECTING_STARTING_PLAYER


def _recover_from_banned_player(state: GameLobbyState, user_id: int) -> None:
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


def _enter_answer_reveal(state: GameLobbyState, resolution: GameResolutionEnum) -> None:
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
        raise BadRequestError(f"Action not allowed during phase {state.phase.value}")


def _deadline(seconds: int) -> datetime:
    return datetime.now(UTC) + timedelta(seconds=seconds)
