from polyfactory.factories.pydantic_factory import ModelFactory

from schemas.user.base import UserCreateSchema


class UserCreateSchemaFactory(ModelFactory[UserCreateSchema]):
    __model__ = UserCreateSchema
