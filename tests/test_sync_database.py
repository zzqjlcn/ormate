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

