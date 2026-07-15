from ormate import ModelRepository
from tests.models import User, UserCreate, UserRead


async def test_async_repository_crud(async_adapter):
    repo = ModelRepository(async_adapter, User, UserRead)
    assert repo.storage_name == "users"
    created = await repo.create_item(UserCreate(id=1, name="Ada", secret="token"))
    assert created.secret == "token"
    assert (await repo.read_item_by_primary_key(1)).name == "Ada"
    updated = await repo.update_item_by_primary_key(1, {"name": "Grace"})
    assert updated.name == "Grace"
    assert await repo.count() == 1
    deleted = await repo.delete_item_by_primary_key(1)
    assert deleted.id == 1
    assert await repo.count() == 0


async def test_bulk_primary_key_operations_and_exists(async_adapter):
    repo = ModelRepository(async_adapter, User, UserRead)
    await repo.create_items(
        [
            {"id": 1, "name": "Ada", "secret": "a"},
            {"id": 2, "name": "Grace", "secret": "b"},
        ]
    )
    assert await repo.exists(User.name == "Ada")
    assert len(await repo.read_items_by_primary_keys([1, 2])) == 2
    assert len(await repo.update_items_by_primary_keys([1, 2], {"name": "Updated"})) == 2
    assert len(await repo.delete_items_by_primary_keys([1, 2])) == 2
    assert not await repo.exists()
