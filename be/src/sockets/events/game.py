import logging
from collections.abc import Awaitable, Callable
from typing import Any

import pydantic

from errors.base import BaseError
from errors.request import BadRequestError, ForbiddenError, NotFoundError
from schemas.lobby.game_state import GameLobbyState
from schemas.socket.events import (
    BanPlayerPayload,
    GameSoundCueName,
    JudgeAnswerPayload,
    SelectPromptPayload,
    SelectStarterPayload,
    UnbanPlayerPayload,
)
from services.game import GameService
from sockets.app import sio
from sockets.broadcast import broadcast_sound_cue, broadcast_state, emit_error
from sockets.namespace import parse_lobby_namespace
from sockets.session import find_sid_for_user, get_socket_session
from sockets.timer_hooks import arm_timer_if_needed
from sockets.uow import build_uow

_logger = logging.getLogger(__name__)


_ERROR_CODES: dict[type[BaseError], str] = {
    BadRequestError: "bad_request",
    ForbiddenError: "forbidden",
    NotFoundError: "not_found",
}


async def _resolve_context(
    namespace: str,
    sid: str,
) -> tuple[int, int] | None:
    """
    Pull lobby_id + user_id out of the connection namespace + session. If
    either is missing, emit a structured error to the sender and return
    ``None`` so the handler bails out.
    """
    lobby_id = parse_lobby_namespace(namespace)
    if lobby_id is None:
        await emit_error(namespace, sid, "bad_request", "Invalid namespace")
        return None
    session = await get_socket_session(sid, namespace)
    if session is None:
        await emit_error(namespace, sid, "unauthorized", "Session missing")
        return None
    return lobby_id, session["user_id"]


async def _run_event[T: pydantic.BaseModel](
    namespace: str,
    sid: str,
    payload: Any,
    payload_schema: type[T] | None,
    action: Callable[[GameService, int, int, T | None], Awaitable[GameLobbyState]],
    sound_cues: Callable[[GameLobbyState, T | None], list[GameSoundCueName]] | None = None,
) -> bool:
    """
    Validate the payload, run ``action`` inside a fresh UoW, broadcast the
    new state, and re-arm any phase-driven timer. Any service-level error is
    caught and emitted back as a structured ``error`` payload to the sender
    so the broadcast contract stays one-way.
    """
    ctx = await _resolve_context(namespace, sid)
    if ctx is None:
        return False
    lobby_id, user_id = ctx

    validated: pydantic.BaseModel | None
    if payload_schema is None:
        validated = None
    else:
        try:
            validated = payload_schema.model_validate(payload or {})
        except pydantic.ValidationError as e:
            await emit_error(namespace, sid, "bad_request", e.errors()[0]["msg"])
            return False

    try:
        async with build_uow() as uow:
            state = await action(GameService(uow), lobby_id, user_id, validated)
    except BaseError as e:
        code = _ERROR_CODES.get(type(e), "error")
        await emit_error(namespace, sid, code, e.detail)
        return False
    except Exception:
        _logger.exception("Unhandled error in socket event for lobby %s", lobby_id)
        await emit_error(namespace, sid, "internal_error", "Internal server error")
        return False

    await broadcast_state(lobby_id, state)
    arm_timer_if_needed(lobby_id, state)
    if sound_cues is not None:
        for cue in sound_cues(state, validated):
            await _emit_sound_cue(lobby_id, cue)
    return True


async def _emit_sound_cue(lobby_id: int, cue: GameSoundCueName) -> None:
    try:
        async with build_uow() as uow:
            payload = await GameService(uow).issue_sound_cue(lobby_id, cue)
        await broadcast_sound_cue(lobby_id, payload)
    except Exception:
        _logger.exception("Failed to emit %s sound cue for lobby %s", cue, lobby_id)


@sio.on("start_game", namespace="*")
async def on_start_game(namespace: str, sid: str, _data: Any = None) -> None:
    async def _action(
        service: GameService,
        lobby_id: int,
        user_id: int,
        _payload: pydantic.BaseModel | None,
    ) -> GameLobbyState:
        return await service.start_game(lobby_id=lobby_id, user_id=user_id)

    await _run_event(
        namespace,
        sid,
        None,
        None,
        _action,
        lambda _state, _payload: [GameSoundCueName.GAME_STARTED],
    )


@sio.on("select_starter", namespace="*")
async def on_select_starter(namespace: str, sid: str, data: Any = None) -> None:
    async def _action(
        service: GameService,
        lobby_id: int,
        user_id: int,
        payload: SelectStarterPayload | None,
    ) -> GameLobbyState:
        assert payload is not None
        return await service.select_starter(
            lobby_id=lobby_id,
            user_id=user_id,
            payload=payload,
        )

    await _run_event(namespace, sid, data, SelectStarterPayload, _action)


@sio.on("select_prompt", namespace="*")
async def on_select_prompt(namespace: str, sid: str, data: Any = None) -> None:
    async def _action(
        service: GameService,
        lobby_id: int,
        user_id: int,
        payload: SelectPromptPayload | None,
    ) -> GameLobbyState:
        assert payload is not None
        return await service.select_prompt(
            lobby_id=lobby_id,
            user_id=user_id,
            payload=payload,
        )

    await _run_event(
        namespace,
        sid,
        data,
        SelectPromptPayload,
        _action,
        lambda _state, _payload: [GameSoundCueName.CLUE_SELECTED],
    )


@sio.on("judge_answer", namespace="*")
async def on_judge_answer(namespace: str, sid: str, data: Any = None) -> None:
    async def _action(
        service: GameService,
        lobby_id: int,
        user_id: int,
        payload: JudgeAnswerPayload | None,
    ) -> GameLobbyState:
        assert payload is not None
        return await service.judge_answer(
            lobby_id=lobby_id,
            user_id=user_id,
            payload=payload,
        )

    def _cues(
        state: GameLobbyState,
        payload: JudgeAnswerPayload | None,
    ) -> list[GameSoundCueName]:
        assert payload is not None
        result = [
            GameSoundCueName.ANSWER_CORRECT if payload.correct else GameSoundCueName.ANSWER_WRONG,
        ]
        if state.phase.value == "answer_reveal":
            result.append(GameSoundCueName.ANSWER_REVEALED)
        return result

    await _run_event(namespace, sid, data, JudgeAnswerPayload, _action, _cues)


@sio.on("buzz", namespace="*")
async def on_buzz(namespace: str, sid: str, _data: Any = None) -> None:
    async def _action(
        service: GameService,
        lobby_id: int,
        user_id: int,
        _payload: pydantic.BaseModel | None,
    ) -> GameLobbyState:
        return await service.buzz(lobby_id=lobby_id, user_id=user_id)

    await _run_event(
        namespace,
        sid,
        None,
        None,
        _action,
        lambda _state, _payload: [GameSoundCueName.BUZZ_ACCEPTED],
    )


@sio.on("advance_answer_reveal", namespace="*")
async def on_advance_answer_reveal(namespace: str, sid: str, _data: Any = None) -> None:
    async def _action(
        service: GameService,
        lobby_id: int,
        user_id: int,
        _payload: pydantic.BaseModel | None,
    ) -> GameLobbyState:
        return await service.advance_answer_reveal(
            lobby_id=lobby_id,
            user_id=user_id,
        )

    await _run_event(
        namespace,
        sid,
        None,
        None,
        _action,
        lambda state, _payload: (
            [GameSoundCueName.GAME_COMPLETED] if state.phase.value == "finished" else []
        ),
    )


@sio.on("ban_player", namespace="*")
async def on_ban_player(namespace: str, sid: str, data: Any = None) -> None:
    async def _action(
        service: GameService,
        lobby_id: int,
        user_id: int,
        payload: BanPlayerPayload | None,
    ) -> GameLobbyState:
        assert payload is not None
        return await service.ban_player(
            lobby_id=lobby_id,
            user_id=user_id,
            payload=payload,
        )

    succeeded = await _run_event(namespace, sid, data, BanPlayerPayload, _action)
    if not succeeded:
        return

    # After ban, force the banned player off the namespace.
    try:
        banned_id = BanPlayerPayload.model_validate(data or {}).user_id
    except pydantic.ValidationError:
        return
    target_sid = await find_sid_for_user(namespace, banned_id)
    if target_sid is not None:
        await sio.disconnect(target_sid, namespace=namespace)


@sio.on("unban_player", namespace="*")
async def on_unban_player(namespace: str, sid: str, data: Any = None) -> None:
    async def _action(
        service: GameService,
        lobby_id: int,
        user_id: int,
        payload: UnbanPlayerPayload | None,
    ) -> GameLobbyState:
        assert payload is not None
        return await service.unban_player(
            lobby_id=lobby_id,
            user_id=user_id,
            payload=payload,
        )

    await _run_event(namespace, sid, data, UnbanPlayerPayload, _action)
