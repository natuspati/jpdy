from schemas.base import BaseSchema


class TokenSchema(BaseSchema):
    access_token: str
    token_type: str = "bearer"


class TokenPayloadSchema(BaseSchema):
    sub: int
    exp: int
