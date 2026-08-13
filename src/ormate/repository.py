from collections.abc import Mapping, Sequence
from typing import Any, cast

from .adapters.base import StorageAdapter
from .projection import read_model_fields
from .protocols import DumpableModel


class ModelRepository[TableModel, ReadModel]:
    """Backend-independent repository with separate write and read models."""

    def __init__(
        self,
        adapter: StorageAdapter,
        model: type[TableModel],
        read_model: type[ReadModel] | None = None,
    ) -> None:
        if not isinstance(adapter, StorageAdapter):
            raise TypeError("adapter must implement StorageAdapter")
        self.adapter = adapter
        self.model = model
        self.read_model = read_model
        self.read_fields = read_model_fields(read_model)

    @property
    def storage_name(self) -> str:
        return self.adapter.storage_name(self.model)

    def to_dict(self, item: Mapping[str, Any] | DumpableModel) -> dict[str, Any]:
        if isinstance(item, Mapping):
            return dict(item)
        if isinstance(item, DumpableModel):
            return item.model_dump(exclude_unset=True)
        raise TypeError(f"Expected a mapping or model_dump()-compatible object, got {type(item).__name__}")

    def encode_for_storage(self, values: dict[str, Any]) -> dict[str, Any]:
        hook = getattr(self.model, "encode_for_storage", None)
        return dict(hook(dict(values))) if callable(hook) else values

    def decode_from_storage(self, values: dict[str, Any]) -> dict[str, Any]:
        hook = getattr(self.read_model, "decode_from_storage", None)
        return dict(hook(dict(values))) if callable(hook) else values

    @staticmethod
    def _validate_pagination(limit: int | None, offset: int | None) -> None:
        if limit is not None and limit < 0:
            raise ValueError("limit cannot be negative")
        if offset is not None and offset < 0:
            raise ValueError("offset cannot be negative")

    @staticmethod
    def _require_query(query: Any, operation: str) -> None:
        if query is None:
            raise ValueError(f"{operation} requires an explicit query; use and_() to match all records")

    def _object_values(self, obj: TableModel | Mapping[str, Any]) -> dict[str, Any]:
        if isinstance(obj, Mapping):
            return dict(obj)
        values: dict[str, Any] = {}
        for field in self.read_fields or ():
            for candidate in field.candidates:
                if hasattr(obj, candidate):
                    values[candidate] = getattr(obj, candidate)
                    break
        if values:
            return values
        return {key: value for key, value in vars(obj).items() if not key.startswith("_")}

    def to_read_model(self, obj: TableModel | Mapping[str, Any]) -> ReadModel | TableModel:
        if self.read_model is None:
            return cast(TableModel, obj)
        values = self.decode_from_storage(self._object_values(obj))
        validator = getattr(self.read_model, "model_validate", None)
        if not callable(validator):
            raise TypeError("read_model must provide model_validate()")
        return cast(ReadModel, validator(values, from_attributes=True))

    async def add(self, item: Mapping[str, Any] | DumpableModel) -> ReadModel | TableModel:
        return (await self.add_many([item]))[0]

    async def add_many(self, items: Sequence[Mapping[str, Any] | DumpableModel]) -> list[ReadModel | TableModel]:
        if not items:
            return []
        values = [self.encode_for_storage(self.to_dict(item)) for item in items]
        objects = await self.adapter.add(self.model, values)
        return [self.to_read_model(obj) for obj in objects]

    async def find(
        self,
        query: Any = None,
        *,
        limit: int | None = None,
        offset: int | None = None,
        statement: Any = None,
    ) -> list[ReadModel | TableModel]:
        self._validate_pagination(limit, offset)
        if limit == 0:
            return []
        objects = await self.adapter.find(
            self.model,
            query,
            limit=limit,
            offset=offset,
            statement=statement,
            projection=self.read_fields,
        )
        return [self.to_read_model(obj) for obj in objects]

    async def find_one(self, query: Any = None) -> ReadModel | TableModel | None:
        items = await self.find(query, limit=1)
        return items[0] if items else None

    async def get(self, primary_key: Any) -> ReadModel | TableModel | None:
        return await self.find_one(self.adapter.primary_key_query(self.model, primary_key))

    async def get_many(self, primary_keys: Sequence[Any]) -> list[ReadModel | TableModel]:
        return await self.find(self.adapter.primary_keys_query(self.model, primary_keys))

    async def update(
        self,
        query: Any,
        item: Mapping[str, Any] | DumpableModel,
    ) -> list[ReadModel | TableModel]:
        self._require_query(query, "update")
        values = self.encode_for_storage(self.to_dict(item))
        if not values:
            raise ValueError("update values cannot be empty")
        objects = await self.adapter.update(self.model, query, values)
        return [self.to_read_model(obj) for obj in objects]

    async def update_by_id(
        self,
        primary_key: Any,
        item: Mapping[str, Any] | DumpableModel,
    ) -> ReadModel | TableModel | None:
        results = await self.update(self.adapter.primary_key_query(self.model, primary_key), item)
        return results[0] if results else None

    async def update_many(
        self,
        primary_keys: Sequence[Any],
        item: Mapping[str, Any] | DumpableModel,
    ) -> list[ReadModel | TableModel]:
        if not primary_keys:
            return []
        return await self.update(self.adapter.primary_keys_query(self.model, primary_keys), item)

    async def remove(self, query: Any) -> list[ReadModel | TableModel]:
        self._require_query(query, "remove")
        objects = await self.adapter.remove(self.model, query)
        return [self.to_read_model(obj) for obj in objects]

    async def remove_by_id(self, primary_key: Any) -> ReadModel | TableModel | None:
        results = await self.remove(self.adapter.primary_key_query(self.model, primary_key))
        return results[0] if results else None

    async def remove_many(self, primary_keys: Sequence[Any]) -> list[ReadModel | TableModel]:
        if not primary_keys:
            return []
        return await self.remove(self.adapter.primary_keys_query(self.model, primary_keys))

    async def count(self, query: Any = None, *, statement: Any = None) -> int:
        return await self.adapter.count(self.model, query, statement=statement)

    async def exists(self, query: Any = None) -> bool:
        return await self.adapter.exists(self.model, query)

    async def execute(self, statement: Any, params: Any = None, **kwargs: Any) -> Any:
        return await self.adapter.execute(statement, params=params, **kwargs)
