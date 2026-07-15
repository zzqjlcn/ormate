from collections.abc import Mapping, Sequence
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class StorageAdapter(Protocol):
    """Backend contract used by ModelRepository."""

    def storage_name(self, model: type[Any]) -> str: ...

    async def create(self, model: type[Any], items: Sequence[Mapping[str, Any]]) -> list[Any]: ...

    async def read(
        self,
        model: type[Any],
        query: Any = None,
        *,
        limit: int | None = None,
        offset: int | None = None,
        statement: Any = None,
    ) -> list[Any]: ...

    async def update(self, model: type[Any], query: Any, values: Mapping[str, Any]) -> list[Any]: ...

    async def delete(self, model: type[Any], query: Any) -> list[Any]: ...

    async def count(self, model: type[Any], query: Any = None, *, statement: Any = None) -> int: ...

    async def exists(self, model: type[Any], query: Any = None) -> bool: ...

    def primary_key_query(self, model: type[Any], primary_key: Any) -> Any: ...

    def primary_keys_query(self, model: type[Any], primary_keys: Sequence[Any]) -> Any: ...

    async def execute(self, statement: Any, params: Any = None, **kwargs: Any) -> Any: ...
