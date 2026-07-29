import asyncio

import pytest
from sqlalchemy import select

from tests.models import User


async def test_async_scope_commits_and_exposes_session(async_db):
    with pytest.raises(RuntimeError):
        _ = async_db.session
    async with async_db as session:
        session.add(User(id=1, name="Ada", secret="x"))
    async with async_db as session:
        assert (await session.scalar(select(User.name))) == "Ada"


async def test_async_scope_rolls_back(async_db):
    with pytest.raises(ValueError):
        async with async_db as session:
            session.add(User(id=1, name="Ada", secret="x"))
            raise ValueError("stop")
    async with async_db as session:
        assert await session.scalar(select(User)) is None


async def test_concurrent_scopes_use_distinct_sessions(async_db):
    sessions = []
    ready = asyncio.Event()

    async def use_scope(user_id):
        async with async_db as session:
            sessions.append(session)
            if len(sessions) == 2:
                ready.set()
            await ready.wait()
            session.add(User(id=user_id, name=str(user_id), secret="x"))

    await asyncio.gather(use_scope(1), use_scope(2))
    assert sessions[0] is not sessions[1]


async def test_new_session_does_not_reuse_current_session(async_db):
    async with async_db as parent:
        async with async_db.new_session() as child:
            assert child is not parent
            assert async_db.session is child

        assert async_db.session is parent


async def test_detached_restores_current_session(async_db):
    async with async_db as parent:
        async with async_db.detached():
            with pytest.raises(RuntimeError):
                _ = async_db.session

        assert async_db.session is parent


async def test_detached_restores_current_session_after_error(async_db):
    async with async_db as parent:
        with pytest.raises(ValueError):
            async with async_db.detached():
                raise ValueError("stop")

        assert async_db.session is parent


async def test_concurrent_new_sessions_are_distinct(async_db):
    sessions = []

    async def use_new_session():
        async with async_db.new_session() as session:
            sessions.append(session)
            await asyncio.sleep(0)

    async with async_db.detached():
        await asyncio.gather(use_new_session(), use_new_session())

    assert len(sessions) == 2
    assert sessions[0] is not sessions[1]
