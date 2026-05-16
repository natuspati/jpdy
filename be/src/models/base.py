import decimal
import uuid
from datetime import date, datetime, time, timedelta
from typing import Any, ClassVar

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.sqltypes import REAL, TIMESTAMP, Integer, String

meta = MetaData()


class DictMixin:
    def to_dict(
        self,
        visited: set | None = None,
        json: bool = False,
    ) -> dict[str, Any] | None:
        if visited is None:
            visited = set()
        object_id = id(self)
        if object_id in visited:
            return None
        visited.add(object_id)
        result = self._build_dict(visited, json)
        return result if result else None

    def _build_dict(self, visited: set, json: bool = False) -> dict[str, Any]:
        model_as_dict = {}
        for key, value in self.__dict__.items():
            if key == "_sa_instance_state":
                continue
            processed_value = self._process_value(value, visited, json)
            if processed_value is not None:
                model_as_dict[key] = processed_value
        return model_as_dict

    def _process_value(self, value: Any, visited: set, json: bool = False) -> Any:
        match value:
            case DictMixin():
                nested_dict = value.to_dict(visited, json)
                return nested_dict if nested_dict else None
            case list() | tuple() | set():
                return self._process_collection(value, visited, json)
            case _ if not json:
                return value
            case datetime() | date() | time():
                return value.isoformat()
            case timedelta():
                return value.total_seconds()
            case decimal.Decimal():
                return float(value)
            case bytes():
                return value.decode("utf-8", errors="ignore")
            case uuid.UUID():
                return str(value)
            case _ if hasattr(value, "__dict__"):
                return str(value)
            case _:
                return value

    def _process_collection(
        self,
        collection: list | tuple | set,
        visited: set,
        json: bool = False,
    ) -> list | None:
        items = [self._process_value(item, visited, json) for item in collection]
        items = [item for item in items if item is not None]
        if json and isinstance(collection, set):
            return list(items) if items else None
        return items if items else None


class Base(DeclarativeBase, DictMixin):
    """Base for all models."""

    metadata = meta
    type_annotation_map: ClassVar = {
        int: Integer,
        float: REAL,
        datetime: TIMESTAMP(timezone=False),
        str: String(256),
    }
