from collections.abc import Mapping, Sequence
from typing import Any, Protocol, runtime_checkable

ExecuteParams = Mapping[str, Any] | Sequence[Mapping[str, Any]]


@runtime_checkable
class DumpableModel(Protocol):
    def model_dump(self, *, exclude_unset: bool = ...) -> dict[str, Any]: ...


class ValidatableModel(Protocol):
    @classmethod
    def model_validate(cls, obj: Any, *, from_attributes: bool = ...) -> Any: ...


type ModelInput = Mapping[str, Any] | DumpableModel
