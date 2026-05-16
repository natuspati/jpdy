from dataclasses import dataclass

from schemas.base import BaseSchema


@dataclass(frozen=True, slots=True)
class ErrorResponse:
    """
    Describes a single OpenAPI error response. Use with
    :func:`utils.route_response.generate_responses` to build the
    ``responses=`` argument of a route decorator.
    """

    status_code: int
    description: str


class ErrorSchema(BaseSchema):
    detail: str
    extra_info: str | dict | None = None
