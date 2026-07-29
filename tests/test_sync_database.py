import pytest
from sqlalchemy import select

from tests.models import User


def test_sync_scope_commits(sync_db):
    with sync_db as session:
        session.add(User(id=1, name="Ada", secret="x"))
    with sync_db as session:
        assert session.scalar(select(User.name)) == "Ada"


def test_sync_scope_rolls_back(sync_db):
    with pytest.raises(ValueError), sync_db as session:
        session.add(User(id=1, name="Ada", secret="x"))
        raise ValueError("stop")
    with sync_db as session:
        assert session.scalar(select(User)) is None


def test_sync_new_session_does_not_reuse_current_session(sync_db):
    with sync_db as parent:
        with sync_db.new_session() as child:
            assert child is not parent
            assert sync_db.session is child

        assert sync_db.session is parent


def test_sync_detached_restores_current_session(sync_db):
    with sync_db as parent:
        with sync_db.detached(), pytest.raises(RuntimeError):
            _ = sync_db.session

        assert sync_db.session is parent


def test_sync_detached_restores_current_session_after_error(sync_db):
    with sync_db as parent:
        with pytest.raises(ValueError), sync_db.detached():
            raise ValueError("stop")

        assert sync_db.session is parent
