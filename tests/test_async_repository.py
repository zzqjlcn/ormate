from ormate import ModelRepository
from tests.models import User, UserCreate, UserRead


async def test_async_repository_crud(async_adapter):
    repo = ModelRepository(async_adapter, User, UserRead)
    assert repo.storage_name == "users"
    created = await repo.add(UserCreate(id=1, name="Ada", secret="token"))
    assert created.secret == "token"
    assert (await repo.get(1)).name == "Ada"
    updated = await repo.update_by_id(1, {"name": "Grace"})
    assert updated.name == "Grace"
    assert await repo.count() == 1
    deleted = await repo.remove_by_id(1)
    assert deleted.id == 1
    assert await repo.count() == 0


async def test_bulk_primary_key_operations_and_exists(async_adapter):
    repo = ModelRepository(async_adapter, User, UserRead)
    await repo.add_many(
        [
            {"id": 1, "name": "Ada", "secret": "a"},
            {"id": 2, "name": "Grace", "secret": "b"},
        ]
    )
    assert await repo.exists(User.name == "Ada")
    assert len(await repo.get_many([1, 2])) == 2
    assert len(await repo.update_many([1, 2], {"name": "Updated"})) == 2
    assert len(await repo.remove_many([1, 2])) == 2
    assert not await repo.exists()
