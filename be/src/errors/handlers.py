import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from configs import settings
from enums import AppEnvironmentEnum
from errors.base import BaseError

_logger = logging.getLogger(__name__)


def add_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(Exception, _handle_uncaught_error)
    app.add_exception_handler(BaseError, _handle_base_error)


async def _handle_uncaught_error(request: Request, exc: Exception) -> JSONResponse:
    _log_error(request, str(exc))
    error_content = {"detail": BaseError.detail}
    if settings.environment is not AppEnvironmentEnum.PROD:
        error_content["extra_info"] = str(exc)
    return JSONResponse(
        content=error_content,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


async def _handle_base_error(request: Request, exc: BaseError) -> JSONResponse:
    _log_error(request, str(exc))
    error_content = {"detail": exc.detail}
    if settings.environment is not AppEnvironmentEnum.PROD and exc.extra_info:
        error_content["extra_info"] = exc.extra_info
    return JSONResponse(
        content=error_content,
        status_code=exc.status_code,
        headers=exc.headers,
    )


def _log_error(request: Request, error_description: str) -> None:
    error_msg = f"Error occurred: {request.method} {request.url}"

    request_cookies = request.cookies
    if request_cookies:
        error_msg += f"\nCookies: {request_cookies}"

    error_msg += f"\n{error_description}"
    _logger.error(error_msg)
