from sqlalchemy import delete, exists, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.media_asset import MediaAsset
from models.prompt import Prompt
from schemas.media import MediaAssetInDBSchema
from utils.model_validation import validate_model


class MediaAssetRepo:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def insert_media_asset(
        self,
        *,
        owner_id: int,
        storage_key: str,
        original_filename: str,
        media_kind: str,
        mime_type: str,
        byte_size: int,
        width: int | None = None,
        height: int | None = None,
    ) -> MediaAssetInDBSchema:
        stmt = (
            insert(MediaAsset)
            .values(
                owner_id=owner_id,
                storage_key=storage_key,
                original_filename=original_filename,
                media_kind=media_kind,
                mime_type=mime_type,
                byte_size=byte_size,
                width=width,
                height=height,
            )
            .returning(MediaAsset)
        )
        asset = (await self._session.execute(stmt)).scalar_one()
        return validate_model(asset, MediaAssetInDBSchema)

    async def select_media_asset(self, asset_id: int) -> MediaAssetInDBSchema | None:
        asset = await self._session.get(MediaAsset, asset_id)
        return validate_model(asset, MediaAssetInDBSchema)

    async def media_asset_is_attached(self, asset_id: int) -> bool:
        stmt = select(
            exists().where(
                (Prompt.question_media_asset_id == asset_id)
                | (Prompt.answer_media_asset_id == asset_id),
            ),
        )
        return bool((await self._session.execute(stmt)).scalar_one())

    async def delete_media_asset(self, asset_id: int) -> bool:
        result = await self._session.execute(
            delete(MediaAsset).where(MediaAsset.id == asset_id),
        )
        return result.rowcount > 0
