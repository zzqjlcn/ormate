from typing import Final

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from ormate.sqlalchemy.database import AsyncDatabase, EngineLike, ensure_database


class DBSessionMiddleware:
    """Pure ASGI transaction middleware for an AsyncDatabase."""

    SCOPE_KEY_PREFIX: Final = "ormate.database"

    def __init__(self, app: ASGIApp, db: EngineLike, *, rollback_on_http_error: bool = False) -> None:
        self.app = app
        database = ensure_database(db)
        if not isinstance(database, AsyncDatabase):
            raise TypeError("DBSessionMiddleware requires an AsyncDatabase or AsyncEngine")
        self.db = database
        self.rollback_on_http_error = rollback_on_http_error
        self.scope_key = f"{self.SCOPE_KEY_PREFIX}:{id(database)}"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in {"http", "websocket"} or scope.get(self.scope_key):
            await self.app(scope, receive, send)
            return

        status_code = 200

        async def capture_status(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        async with self.db.session_scope(scope=id(scope)):
            scope[self.scope_key] = self.db
            try:
                await self.app(scope, receive, capture_status)
                if self.rollback_on_http_error and status_code >= 400:
                    await self.db.rollback()
            except Exception:
                await self.db.rollback()
                raise
