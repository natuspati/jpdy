from fastapi import status


class BaseError(Exception):
    detail: str = "Internal service error"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    headers: dict = {}  # noqa: RUF012 - sub-classes can override, not a class variable
    extra_info: str | dict | None = None

    def __init__(
        self,
        detail: str | None = None,
        status_code: int | None = None,
        headers: dict[str, str] | None = None,
        extra_info: str | dict | None = None,
    ):
        self.detail = detail or self.detail
        self.status_code = status_code or self.status_code
        self.headers = headers or self.headers
        self.extra_info = extra_info or self.extra_info
        super().__init__(self.detail)

    def __str__(self):
        return f"{self.detail} (status_code={self.status_code}) {self.extra_info or ''}"
