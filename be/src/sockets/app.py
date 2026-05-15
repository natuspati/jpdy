import socketio

from configs import settings

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=settings.allowed_hosts,
    namespaces="*",
)
