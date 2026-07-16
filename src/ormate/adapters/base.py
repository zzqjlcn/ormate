from collections.abc import Mapping, Sequence
from typing import Any, Protocol, runtime_checkable

from ormate.projection import ReadField


@runtime_checkable
class StorageAdapter(Protocol):
    """Backend contract used by ModelRepository."""

    def storage_name(self, model: type[Any]) -> str: ...

    async def add(self, model: type[Any], items: Sequence[Mapping[str, Any]]) -> list[Any]: ...

    async def find(
        self,
        model: type[Any],
        query: Any = None,
        *,
        limit: int | None = None,
        offset: int | None = None,
        statement: Any = None,
        projection: Sequence[ReadField] | None = None,
    ) -> list[Any]: ...

    async def update(self, model: type[Any], query: Any, values: Mapping[str, Any]) -> list[Any]: ...

    async def remove(self, model: type[Any], query: Any) -> list[Any]: ...

    async def count(self, model: type[Any], query: Any = None, *, statement: Any = None) -> int: ...

    async def exists(self, model: type[Any], query: Any = None) -> bool: ...

    def primary_key_query(self, model: type[Any], primary_key: Any) -> Any: ...

    def primary_keys_query(self, model: type[Any], primary_keys: Sequence[Any]) -> Any: ...

    async def execute(self, statement: Any, params: Any = None, **kwargs: Any) -> Any: ...
