from collections.abc import Mapping, Sequence
from typing import Any, cast

from .adapters.base import StorageAdapter
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

    def to_read_model(self, obj: TableModel | Mapping[str, Any]) -> ReadModel | TableModel:
        if self.read_model is None:
            return cast(TableModel, obj)
        model_fields = getattr(self.read_model, "model_fields", None)
        field_names = model_fields.keys() if isinstance(model_fields, Mapping) else ()
        if isinstance(obj, Mapping):
            values = dict(obj)
        else:
            values = {field: getattr(obj, field) for field in field_names if hasattr(obj, field)}
            if not values:
                values = {key: value for key, value in vars(obj).items() if not key.startswith("_")}
        values = self.decode_from_storage(values)
        validator = getattr(self.read_model, "model_validate", None)
        if not callable(validator):
            raise TypeError("read_model must provide model_validate()")
        return cast(ReadModel, validator(values, from_attributes=True))

    async def create_item(self, item: Mapping[str, Any] | DumpableModel) -> ReadModel | TableModel:
        return (await self.create_items([item]))[0]

    async def create_items(self, items: Sequence[Mapping[str, Any] | DumpableModel]) -> list[ReadModel | TableModel]:
        if not items:
            return []
        values = [self.encode_for_storage(self.to_dict(item)) for item in items]
        objects = await self.adapter.create(self.model, values)
        return [self.to_read_model(obj) for obj in objects]

    async def read_items(
        self,
        query: Any = None,
        *,
        limit: int | None = None,
        offset: int | None = None,
        statement: Any = None,
    ) -> list[ReadModel | TableModel]:
        objects = await self.adapter.read(
            self.model,
            query,
            limit=limit,
            offset=offset,
            statement=statement,
        )
        return [self.to_read_model(obj) for obj in objects]

    async def read_one_item(self, query: Any = None) -> ReadModel | TableModel | None:
        items = await self.read_items(query, limit=1)
        return items[0] if items else None

    async def read_item_by_primary_key(self, primary_key: Any) -> ReadModel | TableModel | None:
        return await self.read_one_item(self.adapter.primary_key_query(self.model, primary_key))

    async def read_items_by_primary_keys(self, primary_keys: Sequence[Any]) -> list[ReadModel | TableModel]:
        return await self.read_items(self.adapter.primary_keys_query(self.model, primary_keys))

    async def update_items_by_query(
        self,
        query: Any,
        item: Mapping[str, Any] | DumpableModel,
    ) -> list[ReadModel | TableModel]:
        values = self.encode_for_storage(self.to_dict(item))
        objects = await self.adapter.update(self.model, query, values)
        return [self.to_read_model(obj) for obj in objects]

    async def update_item_by_primary_key(
        self,
        primary_key: Any,
        item: Mapping[str, Any] | DumpableModel,
    ) -> ReadModel | TableModel | None:
        results = await self.update_items_by_query(self.adapter.primary_key_query(self.model, primary_key), item)
        return results[0] if results else None

    async def update_items_by_primary_keys(
        self,
        primary_keys: Sequence[Any],
        item: Mapping[str, Any] | DumpableModel,
    ) -> list[ReadModel | TableModel]:
        if not primary_keys:
            return []
        return await self.update_items_by_query(self.adapter.primary_keys_query(self.model, primary_keys), item)

    async def delete_items_by_query(self, query: Any) -> list[ReadModel | TableModel]:
        objects = await self.adapter.delete(self.model, query)
        return [self.to_read_model(obj) for obj in objects]

    async def delete_item_by_primary_key(self, primary_key: Any) -> ReadModel | TableModel | None:
        results = await self.delete_items_by_query(self.adapter.primary_key_query(self.model, primary_key))
        return results[0] if results else None

    async def delete_items_by_primary_keys(self, primary_keys: Sequence[Any]) -> list[ReadModel | TableModel]:
        if not primary_keys:
            return []
        return await self.delete_items_by_query(self.adapter.primary_keys_query(self.model, primary_keys))

    async def count(self, query: Any = None, *, statement: Any = None) -> int:
        return await self.adapter.count(self.model, query, statement=statement)

    async def exists(self, query: Any = None) -> bool:
        return await self.adapter.exists(self.model, query)

    async def execute(self, statement: Any, params: Any = None, **kwargs: Any) -> Any:
        return await self.adapter.execute(statement, params=params, **kwargs)
