from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable, Iterator, Mapping
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from typing import Any, TypeVar

from sqlalchemy import URL, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from .sessions import AsyncSessionScope, SessionScope

T = TypeVar("T")


class Database:
    def __init__(self, engine: Engine, **session_options: Any) -> None:
        self.engine = engine
        session_options.setdefault("expire_on_commit", False)
        self.session_maker = sessionmaker(bind=engine, class_=Session, **session_options)
        self._session_context: ContextVar[Session | None] = ContextVar(f"ormate_sync_{id(self)}", default=None)
        self._scope_stack: ContextVar[tuple[SessionScope, ...]] = ContextVar(
            f"ormate_sync_scope_stack_{id(self)}", default=()
        )

    @classmethod
    def create(
        cls,
        url: str | URL,
        *,
        session_options: Mapping[str, Any] | None = None,
        **engine_options: Any,
    ) -> Database:
        return cls(create_engine(url, **engine_options), **dict(session_options or {}))

    @property
    def session(self) -> Session:
        session = self._session_context.get()
        if session is None:
            raise RuntimeError("No active database scope; use 'with db:' or 'with db.session_scope()'.")
        return session

    def __enter__(self) -> Session:
        scope = self.session_scope()
        self._scope_stack.set((*self._scope_stack.get(), scope))
        return scope.__enter__()

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        stack = self._scope_stack.get()
        if not stack:
            raise RuntimeError("Database scope stack is empty")
        scope = stack[-1]
        try:
            scope.__exit__(exc_type, exc_value, traceback)
        finally:
            self._scope_stack.set(stack[:-1])

    def session_scope(self, scope: Any = None) -> SessionScope:
        return SessionScope(self, scope)

    @contextmanager
    def session_generator(self) -> Iterator[Session]:
        current = self._session_context.get()
        if current is not None:
            yield current
            return
        with self.session_scope() as session:
            yield session

    def run(self, fn: Callable[..., T], *args: Any, is_session: bool = True, **kwargs: Any) -> T:
        if is_session:
            with self.session_generator() as session:
                return fn(session, *args, **kwargs)
        with self.engine.begin() as connection:
            return fn(connection, *args, **kwargs)

    async def async_run(self, fn: Callable[..., T], *args: Any, is_session: bool = True, **kwargs: Any) -> T:
        return await asyncio.to_thread(lambda: self.run(fn, *args, is_session=is_session, **kwargs))

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def close(self) -> None:
        self.engine.dispose()

    async def dispose(self) -> None:
        await asyncio.to_thread(self.close)


class AsyncDatabase:
    def __init__(self, engine: AsyncEngine, **session_options: Any) -> None:
        self.engine = engine
        session_options.setdefault("expire_on_commit", False)
        self.session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, **session_options)
        self._session_context: ContextVar[AsyncSession | None] = ContextVar(f"ormate_async_{id(self)}", default=None)
        self._scope_stack: ContextVar[tuple[AsyncSessionScope, ...]] = ContextVar(
            f"ormate_async_scope_stack_{id(self)}", default=()
        )

    @classmethod
    def create(
        cls, url: str | URL, *, session_options: Mapping[str, Any] | None = None, **engine_options: Any
    ) -> AsyncDatabase:
        return cls(create_async_engine(url, **engine_options), **dict(session_options or {}))

    @property
    def session(self) -> AsyncSession:
        session = self._session_context.get()
        if session is None:
            raise RuntimeError("No active database scope; use 'async with db'.")
        return session

    async def __aenter__(self) -> AsyncSession:
        scope = self.session_scope()
        self._scope_stack.set((*self._scope_stack.get(), scope))
        return await scope.__aenter__()

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        stack = self._scope_stack.get()
        if not stack:
            raise RuntimeError("Async database scope stack is empty")
        scope = stack[-1]
        try:
            await scope.__aexit__(exc_type, exc_value, traceback)
        finally:
            self._scope_stack.set(stack[:-1])

    def session_scope(self, scope: Any = None) -> AsyncSessionScope:
        return AsyncSessionScope(self, scope)

    @asynccontextmanager
    async def session_generator(self) -> AsyncIterator[AsyncSession]:
        current = self._session_context.get()
        if current is not None:
            yield current
            return
        async with self.session_scope() as session:
            yield session

    async def async_run(self, fn: Callable[..., T], *args: Any, is_session: bool = True, **kwargs: Any) -> T:
        if is_session:
            async with self.session_generator() as session:
                return await session.run_sync(fn, *args, **kwargs)
        async with self.engine.begin() as connection:
            return await connection.run_sync(fn, *args, **kwargs)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def dispose(self) -> None:
        await self.engine.dispose()


DatabaseLike = Database | AsyncDatabase
EngineLike = Engine | AsyncEngine | DatabaseLike


def ensure_database(engine: EngineLike) -> DatabaseLike:
    if isinstance(engine, (Database, AsyncDatabase)):
        return engine
    if isinstance(engine, AsyncEngine):
        return AsyncDatabase(engine)
    if isinstance(engine, Engine):
        return Database(engine)
    raise TypeError(f"Unsupported database engine: {type(engine).__name__}")
