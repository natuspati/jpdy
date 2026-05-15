import logging

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

import routes
import sockets.events  # noqa: F401  # registers socket.io event handlers
from configs import settings
from errors import add_error_handlers
from lifespan import lifespan
from sockets.app import sio

_logger = logging.getLogger(__name__)

fastapi_app = FastAPI(
    title=settings.name,
    version=settings.version,
    lifespan=lifespan,
    openapi_url=None,
    docs_url=None,
    redoc_url=None,
)

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_hosts,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

fastapi_app.include_router(routes.router)


@fastapi_app.get("/", include_in_schema=False)
async def redirect_to_docs() -> RedirectResponse:
    return RedirectResponse(url=fastapi_app.url_path_for("get_swagger_documentation"))


add_error_handlers(fastapi_app)

app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app, socketio_path="ws")

_logger.warning(
    "Finished setting application up, "
    f"version: {settings.version}, "
    f"environment: {settings.environment}",
)
