from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ReadField:
    """A ReadModel field and its ordered storage-field candidates."""

    name: str
    candidates: tuple[str, ...]


def read_model_fields(read_model: type[Any] | None) -> tuple[ReadField, ...] | None:
    if read_model is None:
        return None
    model_fields = getattr(read_model, "model_fields", None)
    if not isinstance(model_fields, dict):
        return None

    result: list[ReadField] = []
    for name, field in model_fields.items():
        validation_alias = getattr(field, "validation_alias", None)
        if validation_alias is None:
            candidates = (name,)
        elif isinstance(validation_alias, str):
            candidates = (validation_alias,)
        elif hasattr(validation_alias, "choices"):
            choices = tuple(validation_alias.choices)
            if not choices or not all(isinstance(choice, str) for choice in choices):
                raise TypeError(f"ReadModel field {name!r} must use string-only AliasChoices")
            candidates = choices
        elif hasattr(validation_alias, "path"):
            raise TypeError(f"ReadModel field {name!r} uses AliasPath, which cannot be projected automatically")
        else:
            raise TypeError(f"Unsupported validation alias on ReadModel field {name!r}")
        result.append(ReadField(name=name, candidates=candidates))
    return tuple(result)
