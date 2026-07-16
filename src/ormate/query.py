from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal, Protocol


class FieldReference(Protocol):
    """Mapped field object accepted by query helpers."""

    @property
    def key(self) -> str: ...


type QueryField = str | FieldReference


@dataclass(frozen=True, slots=True)
class QueryExpression:
    """Base type for backend-independent structured filters."""


@dataclass(frozen=True, slots=True)
class Constant(QueryExpression):
    value: bool


@dataclass(frozen=True, slots=True)
class Comparison(QueryExpression):
    field: str
    operator: Literal["eq", "ne", "gt", "gte", "lt", "lte"]
    value: Any


@dataclass(frozen=True, slots=True)
class SetComparison(QueryExpression):
    field: str
    values: tuple[Any, ...]
    negated: bool = False


@dataclass(frozen=True, slots=True)
class BooleanExpression(QueryExpression):
    operator: Literal["and", "or"]
    expressions: tuple[QueryExpression, ...]


@dataclass(frozen=True, slots=True)
class NotExpression(QueryExpression):
    expression: QueryExpression


def _field(value: QueryField) -> str:
    if isinstance(value, str):
        if value:
            return value
        raise ValueError("query field must be a non-empty string")
    key = getattr(value, "key", None)
    if isinstance(key, str) and key:
        return key
    raise TypeError("query field must be a non-empty string or a mapped field with a string key")


def _expression(value: QueryExpression) -> QueryExpression:
    if not isinstance(value, QueryExpression):
        raise TypeError("and_(), or_(), and not_() only accept ormate query expressions")
    return value


def eq(field: QueryField, value: Any) -> QueryExpression:
    return Comparison(_field(field), "eq", value)


def ne(field: QueryField, value: Any) -> QueryExpression:
    return Comparison(_field(field), "ne", value)


def gt(field: QueryField, value: Any) -> QueryExpression:
    return Comparison(_field(field), "gt", value)


def gte(field: QueryField, value: Any) -> QueryExpression:
    return Comparison(_field(field), "gte", value)


def lt(field: QueryField, value: Any) -> QueryExpression:
    return Comparison(_field(field), "lt", value)


def lte(field: QueryField, value: Any) -> QueryExpression:
    return Comparison(_field(field), "lte", value)


def in_(field: QueryField, values: Sequence[Any]) -> QueryExpression:
    items = tuple(values)
    return SetComparison(_field(field), items) if items else Constant(False)


def not_in(field: QueryField, values: Sequence[Any]) -> QueryExpression:
    items = tuple(values)
    return SetComparison(_field(field), items, negated=True) if items else Constant(True)


def _combine(operator: Literal["and", "or"], expressions: tuple[QueryExpression, ...]) -> QueryExpression:
    checked = tuple(_expression(expression) for expression in expressions)
    if not checked:
        return Constant(operator == "and")
    flattened: list[QueryExpression] = []
    for expression in checked:
        if isinstance(expression, BooleanExpression) and expression.operator == operator:
            flattened.extend(expression.expressions)
        else:
            flattened.append(expression)
    return flattened[0] if len(flattened) == 1 else BooleanExpression(operator, tuple(flattened))


def and_(*expressions: QueryExpression) -> QueryExpression:
    return _combine("and", expressions)


def or_(*expressions: QueryExpression) -> QueryExpression:
    return _combine("or", expressions)


def not_(expression: QueryExpression) -> QueryExpression:
    return NotExpression(_expression(expression))
