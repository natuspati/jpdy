from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ErrorResponse:
    """
    Describes a single OpenAPI error response. Use with
    :func:`utils.route_response.generate_responses` to build the
    ``responses=`` argument of a route decorator.
    """

    status_code: int
    description: str
