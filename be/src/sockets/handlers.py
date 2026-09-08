from sockets.app import sio
from sockets.events.connection import on_connect, on_disconnect
from sockets.events.game import (
    on_advance_answer_reveal,
    on_ban_player,
    on_buzz,
    on_judge_answer,
    on_select_prompt,
    on_select_starter,
    on_start_game,
    on_unban_player,
)


def register_socket_handlers() -> None:
    """Register Socket.IO handlers during explicit application setup."""
    sio.on("connect", handler=on_connect, namespace="*")
    sio.on("disconnect", handler=on_disconnect, namespace="*")
    sio.on("start_game", handler=on_start_game, namespace="*")
    sio.on("select_starter", handler=on_select_starter, namespace="*")
    sio.on("select_prompt", handler=on_select_prompt, namespace="*")
    sio.on("judge_answer", handler=on_judge_answer, namespace="*")
    sio.on("buzz", handler=on_buzz, namespace="*")
    sio.on("advance_answer_reveal", handler=on_advance_answer_reveal, namespace="*")
    sio.on("ban_player", handler=on_ban_player, namespace="*")
    sio.on("unban_player", handler=on_unban_player, namespace="*")
