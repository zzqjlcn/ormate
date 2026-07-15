from sqlalchemy import select
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from ormate.web import DBSessionMiddleware
from tests.models import User


def test_web_middleware_commits_success(async_db):
    async def create(request):
        async_db.session.add(User(id=1, name="Ada", secret="x"))
        return JSONResponse({"ok": True})

    app = Starlette(routes=[Route("/", create, methods=["POST"])])
    app.add_middleware(DBSessionMiddleware, db=async_db)
    with TestClient(app) as client:
        assert client.post("/").status_code == 200

    async def check():
        async with async_db as session:
            return await session.scalar(select(User.name))

    import asyncio

    assert asyncio.run(check()) == "Ada"
