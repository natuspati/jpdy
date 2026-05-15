from fastapi import APIRouter, Depends, Request
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse

from auth import check_basic_auth

router = APIRouter(tags=["internal"], include_in_schema=False)


@router.get("/health")
async def health(request: Request) -> dict[str, str]:
    return {"status": "healthy", "version": request.app.version}


@router.get("/docs", dependencies=[Depends(check_basic_auth)])
async def get_swagger_documentation(request: Request) -> HTMLResponse:
    return get_swagger_ui_html(
        openapi_url=request.app.url_path_for("get_openapi_schema"),
        title=request.app.title + " - Swagger UI",
    )


@router.get("/redoc", dependencies=[Depends(check_basic_auth)])
async def get_redoc_documentation(request: Request) -> HTMLResponse:
    return get_redoc_html(
        openapi_url=request.app.url_path_for("get_openapi_schema"),
        title=request.app.title + " - ReDoc",
    )


@router.get("/openapi.json", dependencies=[Depends(check_basic_auth)])
async def get_openapi_schema(request: Request) -> dict:
    return get_openapi(
        title=request.app.title,
        version=request.app.version,
        openapi_version=request.app.openapi_version,
        description=request.app.description,
        routes=request.app.routes,
    )
