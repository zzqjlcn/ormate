import asyncio

import pytest
from sqlalchemy import select
from starlette.applications import Starlette
from starlette.background import BackgroundTask
from starlette.responses import JSONResponse
from starlette.routing import Route, WebSocketRoute
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

    assert asyncio.run(check()) == "Ada"


def test_web_middleware_finishes_request_session_before_background_task(async_db):
    async def background():
        with pytest.raises(RuntimeError):
            _ = async_db.session
        async with async_db as session:
            session.add(User(id=2, name="Background", secret="y"))

    async def create(request):
        async_db.session.add(User(id=1, name="Request", secret="x"))
        return JSONResponse({"ok": True}, background=BackgroundTask(background))

    app = Starlette(routes=[Route("/", create, methods=["POST"])])
    app.add_middleware(DBSessionMiddleware, db=async_db)
    with TestClient(app) as client:
        assert client.post("/").status_code == 200

    async def check():
        async with async_db as session:
            return list((await session.scalars(select(User.name).order_by(User.id))).all())

    assert asyncio.run(check()) == ["Request", "Background"]


def test_web_middleware_does_not_scope_websockets(async_db):
    async def websocket_endpoint(websocket):
        await websocket.accept()
        with pytest.raises(RuntimeError):
            _ = async_db.session
        await websocket.send_text("ok")
        await websocket.close()

    app = Starlette(routes=[WebSocketRoute("/ws", websocket_endpoint)])
    app.add_middleware(DBSessionMiddleware, db=async_db)
    with TestClient(app) as client, client.websocket_connect("/ws") as websocket:
        assert websocket.receive_text() == "ok"


def test_web_middleware_rolls_back_http_errors(async_db):
    async def create(request):
        async_db.session.add(User(id=1, name="Rejected", secret="x"))
        return JSONResponse({"ok": False}, status_code=400)

    app = Starlette(routes=[Route("/", create, methods=["POST"])])
    app.add_middleware(DBSessionMiddleware, db=async_db, rollback_on_http_error=True)
    with TestClient(app) as client:
        assert client.post("/").status_code == 400

    async def check():
        async with async_db as session:
            return await session.scalar(select(User))

    assert asyncio.run(check()) is None
