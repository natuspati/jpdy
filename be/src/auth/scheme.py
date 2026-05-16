from fastapi.security import HTTPBasic, OAuth2PasswordBearer

basic_security = HTTPBasic(
    description="Authentication for internal routes",
    auto_error=False,
)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="api/v1/user/sign-in",
    description="JWT bearer token for end-user routes",
    auto_error=False,
)
