from collections.abc import Mapping
from types import MappingProxyType

from fastapi import status


class BaseError(Exception):
    detail: str = "Internal service error"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    headers: Mapping[str, str] = MappingProxyType({})
    extra_info: str | dict | None = None

    def __init__(
        self,
        detail: str | None = None,
        status_code: int | None = None,
        headers: dict[str, str] | None = None,
        extra_info: str | dict | None = None,
    ):
        self.detail = detail if detail is not None else self.detail
        self.status_code = status_code if status_code is not None else self.status_code
        self.headers = dict(self.headers) if headers is None else dict(headers)
        self.extra_info = extra_info if extra_info is not None else self.extra_info
        super().__init__(self.detail)

    def __str__(self):
        return f"{self.detail} (status_code={self.status_code}) {self.extra_info or ''}"
