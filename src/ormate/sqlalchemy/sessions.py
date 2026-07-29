from __future__ import annotations

from contextvars import Token
from types import TracebackType
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session


class SessionScope:
    def __init__(self, db: Any, scope: Any = None, *, reuse_current: bool = True) -> None:
        self.db = db
        self.scope = scope
        self.reuse_current = reuse_current
        self.token: Token[Any] | None = None
        self.session: Session | None = None
        self.owned = False

    def __enter__(self) -> Session:
        current = self.db._session_context.get()
        if isinstance(self.scope, Session):
            self.session = self.scope
        elif self.reuse_current and current is not None:
            self.session = current
        else:
            self.session = self.db.session_maker()
            self.owned = True
        self.token = self.db._session_context.set(self.session)
        return self.session

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            if self.owned and self.session is not None:
                if exc_type is None:
                    self.session.commit()
                else:
                    self.session.rollback()
            elif exc_type is not None and self.session is not None:
                self.session.rollback()
        finally:
            if self.owned and self.session is not None:
                self.session.close()
            if self.token is not None:
                self.db._session_context.reset(self.token)


class AsyncSessionScope:
    def __init__(self, db: Any, scope: Any = None, *, reuse_current: bool = True) -> None:
        self.db = db
        self.scope = scope
        self.reuse_current = reuse_current
        self.token: Token[Any] | None = None
        self.session: AsyncSession | None = None
        self.owned = False

    async def __aenter__(self) -> AsyncSession:
        current = self.db._session_context.get()
        if isinstance(self.scope, AsyncSession):
            self.session = self.scope
        elif self.reuse_current and current is not None:
            self.session = current
        else:
            self.session = self.db.session_maker()
            self.owned = True
        self.token = self.db._session_context.set(self.session)
        return self.session

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            if self.owned and self.session is not None:
                if exc_type is None:
                    await self.session.commit()
                else:
                    await self.session.rollback()
            elif exc_type is not None and self.session is not None:
                await self.session.rollback()
        finally:
            if self.owned and self.session is not None:
                await self.session.close()
            if self.token is not None:
                self.db._session_context.reset(self.token)
