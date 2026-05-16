from sqlalchemy.ext.asyncio import AsyncSession


class LobbyRepo:
    def __init__(self, session: AsyncSession):
        self._session = session
