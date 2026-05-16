from polyfactory.factories.pydantic_factory import ModelFactory

from schemas.lobby.base import LobbyCreateSchema, LobbyUpdateSchema


class LobbyCreateSchemaFactory(ModelFactory[LobbyCreateSchema]):
    __model__ = LobbyCreateSchema


class LobbyUpdateSchemaFactory(ModelFactory[LobbyUpdateSchema]):
    __model__ = LobbyUpdateSchema
