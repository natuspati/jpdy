from schemas.base import BaseSchema


class SelectStarterPayload(BaseSchema):
    user_id: int


class SelectPromptPayload(BaseSchema):
    prompt_id: int


class JudgeAnswerPayload(BaseSchema):
    correct: bool


class BanPlayerPayload(BaseSchema):
    user_id: int


class UnbanPlayerPayload(BaseSchema):
    user_id: int


class SocketErrorPayload(BaseSchema):
    code: str
    detail: str
