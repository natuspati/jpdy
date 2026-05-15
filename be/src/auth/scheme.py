from fastapi.security import HTTPBasic

basic_security = HTTPBasic(
    description="Authentication for internal routes",
    auto_error=False,
)
