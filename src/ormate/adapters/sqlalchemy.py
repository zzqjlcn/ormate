from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import Select, and_, false, func, inspect, or_, select, true
from sqlalchemy.engine import Result
from sqlalchemy.orm import Session
from sqlalchemy.sql import Executable

from ormate.projection import ReadField
from ormate.query import BooleanExpression, Comparison, Constant, NotExpression, QueryExpression, SetComparison
from ormate.sqlalchemy.database import AsyncDatabase, DatabaseLike, EngineLike, ensure_database


class SQLAlchemyAdapter:
    """Storage adapter for SQLAlchemy Declarative and SQLModel table models."""

    def __init__(self, database: EngineLike) -> None:
        self.database: DatabaseLike = ensure_database(database)

    def select(self, model: type[Any]) -> Select[tuple[Any]]:
        return select(model)

    def _mapper(self, model: type[Any]) -> Any:
        mapper = inspect(model)
        if mapper is None:
            raise TypeError(f"{model!r} is not a mapped SQLAlchemy model")
        return mapper

    def storage_name(self, model: type[Any]) -> str:
        return str(self._mapper(model).local_table.name)

    def _column(self, model: type[Any], field: str) -> Any:
        mapper = self._mapper(model)
        if field not in mapper.columns:
            raise ValueError(f"Unknown query field {field!r} for storage model {model.__name__}")
        return mapper.columns[field]

    def _compile_query(self, model: type[Any], query: Any) -> Any:
        if not isinstance(query, QueryExpression):
            return query
        if isinstance(query, Constant):
            return true() if query.value else false()
        if isinstance(query, Comparison):
            column = self._column(model, query.field)
            operators = {
                "eq": column.__eq__,
                "ne": column.__ne__,
                "gt": column.__gt__,
                "gte": column.__ge__,
                "lt": column.__lt__,
                "lte": column.__le__,
            }
            return operators[query.operator](query.value)
        if isinstance(query, SetComparison):
            expression = self._column(model, query.field).in_(query.values)
            return ~expression if query.negated else expression
        if isinstance(query, BooleanExpression):
            expressions = [self._compile_query(model, expression) for expression in query.expressions]
            return and_(*expressions) if query.operator == "and" else or_(*expressions)
        if isinstance(query, NotExpression):
            return ~self._compile_query(model, query.expression)
        raise TypeError(f"Unsupported query expression: {type(query).__name__}")

    def _projection_columns(self, model: type[Any], projection: Sequence[ReadField]) -> list[Any]:
        mapper = self._mapper(model)
        columns = []
        for read_field in projection:
            storage_field = next((name for name in read_field.candidates if name in mapper.columns), None)
            if storage_field is None:
                candidates = ", ".join(repr(name) for name in read_field.candidates)
                raise ValueError(
                    f"ReadModel field {read_field.name!r} resolved to [{candidates}], but none exists "
                    f"on storage model {model.__name__}"
                )
            columns.append(mapper.columns[storage_field].label(storage_field))
        return columns

    def primary_key_query(self, model: type[Any], primary_key: Any) -> Any:
        primary_keys = tuple(self._mapper(model).primary_key)
        if len(primary_keys) == 1:
            values = (primary_key,)
        elif isinstance(primary_key, Mapping):
            try:
                values = tuple(primary_key[column.key] for column in primary_keys)
            except KeyError as exc:
                raise ValueError(f"Missing composite primary-key field: {exc.args[0]}") from exc
        elif isinstance(primary_key, tuple) and len(primary_key) == len(primary_keys):
            values = primary_key
        else:
            raise ValueError("Composite primary keys require a mapping or a tuple with one value per key")
        return and_(*(column == value for column, value in zip(primary_keys, values, strict=True)))

    def primary_keys_query(self, model: type[Any], primary_keys: Sequence[Any]) -> Any:
        if not primary_keys:
            return false()
        mapped_keys = tuple(self._mapper(model).primary_key)
        if len(mapped_keys) == 1:
            return mapped_keys[0].in_(primary_keys)
        return or_(*(self.primary_key_query(model, primary_key) for primary_key in primary_keys))

    async def add(self, model: type[Any], items: Sequence[Mapping[str, Any]]) -> list[Any]:
        def operation(session: Session) -> list[Any]:
            objects = [model(**values) for values in items]
            session.add_all(objects)
            session.flush()
            for obj in objects:
                session.refresh(obj)
            return objects

        return await self.database.async_run(operation)

    async def find(
        self,
        model: type[Any],
        query: Any = None,
        *,
        limit: int | None = None,
        offset: int | None = None,
        statement: Select[Any] | None = None,
        projection: Sequence[ReadField] | None = None,
    ) -> list[Any]:
        stmt = statement if statement is not None else self.select(model)
        if query is not None:
            stmt = stmt.where(self._compile_query(model, query))
        if offset is not None:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)

        if projection is not None:
            stmt = stmt.with_only_columns(*self._projection_columns(model, projection), maintain_column_froms=True)

        def operation(session: Session) -> list[Any]:
            result = session.execute(stmt)
            return list(result.mappings().all()) if projection is not None else list(result.scalars().all())

        return await self.database.async_run(operation)

    async def update(self, model: type[Any], query: Any, values: Mapping[str, Any]) -> list[Any]:
        mapper = self._mapper(model)
        mapped_fields = {attribute.key for attribute in mapper.column_attrs}

        def operation(session: Session) -> list[Any]:
            objects = list(session.scalars(self.select(model).where(self._compile_query(model, query))).all())
            for obj in objects:
                for key, value in values.items():
                    if key in mapped_fields:
                        setattr(obj, key, value)
            session.flush()
            for obj in objects:
                session.refresh(obj)
            return objects

        return await self.database.async_run(operation)

    async def remove(self, model: type[Any], query: Any) -> list[Any]:
        def operation(session: Session) -> list[Any]:
            objects = list(session.scalars(self.select(model).where(self._compile_query(model, query))).all())
            for obj in objects:
                session.delete(obj)
            session.flush()
            return objects

        return await self.database.async_run(operation)

    async def count(self, model: type[Any], query: Any = None, *, statement: Select[Any] | None = None) -> int:
        stmt = statement if statement is not None else self.select(model)
        if query is not None:
            stmt = stmt.where(self._compile_query(model, query))

        def operation(session: Session) -> int:
            count_statement = select(func.count()).select_from(stmt.order_by(None).subquery())
            return int(session.scalar(count_statement) or 0)

        return await self.database.async_run(operation)

    async def exists(self, model: type[Any], query: Any = None) -> bool:
        statement = select(1).select_from(model)
        if query is not None:
            statement = statement.where(self._compile_query(model, query))
        statement = statement.limit(1)

        def operation(session: Session) -> bool:
            return session.scalar(statement) is not None

        return await self.database.async_run(operation)

    async def execute(
        self,
        statement: Executable,
        params: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
        **kwargs: Any,
    ) -> Result[Any]:
        def operation(session: Session) -> Result[Any]:
            return session.execute(statement, params=params, **kwargs)

        if isinstance(self.database, AsyncDatabase):
            async with self.database.session_generator() as session:
                return await session.execute(statement, params=params, **kwargs)
        return await self.database.async_run(operation)
