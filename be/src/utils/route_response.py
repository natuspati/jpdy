from typing import Any

from schemas.error import ErrorResponse


def generate_responses(
    *responses: ErrorResponse,
) -> dict[int | str, dict[str, Any]]:
    """
    Convert a sequence of :class:`ErrorResponse` dataclasses into the dict
    shape FastAPI expects in a route's ``responses=`` decorator argument.

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
            result[response.status_code] = {"description": response.description}
        else:
            existing["description"] = f"{existing['description']}; {response.description}"
    return result
