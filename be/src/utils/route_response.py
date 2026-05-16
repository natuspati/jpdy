from typing import Any

from schemas.error import ErrorResponse, ErrorSchema


def generate_responses(
    *responses: ErrorResponse,
) -> dict[int | str, dict[str, Any]]:
    """
    Convert a sequence of :class:`ErrorResponse` dataclasses into the dict
    shape FastAPI expects in a route's ``responses=`` decorator argument.

    Every entry is tagged with ``model=ErrorSchema`` so the OpenAPI document
    shows the actual JSON body (``{"detail": "...", "extra_info": ...}``) the
    error handlers in ``errors/handlers.py`` produce.

    Multiple ``ErrorResponse`` values that share a status code have their
    descriptions concatenated, so every failure mode for a given code stays
    visible in the OpenAPI document.

    :param responses: one or more error responses to document
    :return: mapping suitable for ``@router.get(..., responses=...)``
    """
    result: dict[int | str, dict[str, Any]] = {}
    for response in responses:
        existing = result.get(response.status_code)
        if existing is None:
            result[response.status_code] = {
                "description": response.description,
                "model": ErrorSchema,
            }
        else:
            existing["description"] = f"{existing['description']}; {response.description}"
    return result
