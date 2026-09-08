import socketio

from configs import settings

_manager = (
    socketio.AsyncRedisManager(
        settings.socketio_redis_url,
        channel=settings.socketio_redis_channel,
    )
    if settings.socketio_redis_url
    else None
)

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=settings.allowed_hosts,
    namespaces="*",
    client_manager=_manager,
)
