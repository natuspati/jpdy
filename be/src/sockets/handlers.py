from sockets.app import sio
from sockets.events.connection import on_connect, on_disconnect
from sockets.events.game import (
    on_advance_answer_reveal,
    on_advance_final_reveal,
    on_advance_round,
    on_ban_player,
    on_buzz,
    on_judge_answer,
    on_judge_final_answer,
    on_place_bet,
    on_select_prompt,
    on_select_starter,
    on_set_assets_loaded,
    on_start_game,
    on_submit_final_answer,
    on_submit_final_wager,
    on_unban_player,
)
from sockets.events.lobby_list import on_lobby_list_connect
from sockets.namespace import LOBBY_LIST_NAMESPACE


def register_socket_handlers() -> None:
    """Register Socket.IO handlers during explicit application setup."""
    # An explicit handler wins over the "*" catch-all, so this namespace never reaches on_connect.
    sio.on("connect", handler=on_lobby_list_connect, namespace=LOBBY_LIST_NAMESPACE)
    sio.on("connect", handler=on_connect, namespace="*")
    sio.on("disconnect", handler=on_disconnect, namespace="*")
    sio.on("set_assets_loaded", handler=on_set_assets_loaded, namespace="*")
    sio.on("start_game", handler=on_start_game, namespace="*")
    sio.on("select_starter", handler=on_select_starter, namespace="*")
    sio.on("select_prompt", handler=on_select_prompt, namespace="*")
    sio.on("judge_answer", handler=on_judge_answer, namespace="*")
    sio.on("place_bet", handler=on_place_bet, namespace="*")
    sio.on("buzz", handler=on_buzz, namespace="*")
    sio.on("advance_answer_reveal", handler=on_advance_answer_reveal, namespace="*")
    sio.on("advance_round", handler=on_advance_round, namespace="*")
    sio.on("ban_player", handler=on_ban_player, namespace="*")
    sio.on("unban_player", handler=on_unban_player, namespace="*")
    sio.on("submit_final_wager", handler=on_submit_final_wager, namespace="*")
    sio.on("submit_final_answer", handler=on_submit_final_answer, namespace="*")
    sio.on("judge_final_answer", handler=on_judge_final_answer, namespace="*")
    sio.on("advance_final_reveal", handler=on_advance_final_reveal, namespace="*")
