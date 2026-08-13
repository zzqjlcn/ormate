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
        if scope["type"] != "http" or scope.get(self.scope_key):
            await self.app(scope, receive, send)
            return

        status_code = 200
        session_scope = self.db.session_scope()
        await session_scope.__aenter__()
        scope[self.scope_key] = self.db
        finalized = False

        async def finalize(exc: BaseException | None = None) -> None:
            nonlocal finalized
            if finalized:
                return
            finalized = True
            exc_type = type(exc) if exc is not None else None
            traceback = exc.__traceback__ if exc is not None else None
            await session_scope.__aexit__(exc_type, exc, traceback)

        async def capture_status(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)
            if message["type"] == "http.response.body" and not message.get("more_body", False):
                if self.rollback_on_http_error and status_code >= 400:
                    await self.db.rollback()
                await finalize()

        try:
            await self.app(scope, receive, capture_status)
        except BaseException as exc:
            await finalize(exc)
            raise
        finally:
            await finalize()
