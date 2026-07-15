from ormate import ModelRepository
from tests.models import User, UserCreate, UserRead, UserUpdate


async def test_separate_create_update_read_models(async_db, async_adapter):
    repo = ModelRepository(async_adapter, User, UserRead)
    await repo.create_item(UserCreate(id=1, name="Ada", secret="plain"))
    updated = await repo.update_item_by_primary_key(1, UserUpdate(name="Grace"))
    assert updated.name == "Grace"
    assert updated.secret == "plain"

    async with async_db as session:
        stored = await session.get(User, 1)
        assert stored.secret == "nialp"
