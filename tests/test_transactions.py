import pytest

from ormate import ModelRepository
from tests.models import User


async def test_multiple_repository_calls_are_atomic(async_db, async_adapter):
    repo = ModelRepository(async_adapter, User)
    with pytest.raises(RuntimeError):
        async with async_db:
            await repo.create_item({"id": 1, "name": "Ada", "secret": "x"})
            await repo.create_item({"id": 2, "name": "Grace", "secret": "y"})
            raise RuntimeError("rollback all")
    assert await repo.count() == 0


async def test_nested_scope_exception_marks_shared_transaction_for_rollback(async_db, async_adapter):
    repo = ModelRepository(async_adapter, User)
    async with async_db:
        await repo.create_item({"id": 1, "name": "Ada", "secret": "x"})
        with pytest.raises(ValueError):
            async with async_db:
                raise ValueError("rollback shared transaction")
    assert await repo.count() == 0
