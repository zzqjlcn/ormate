from ormate import ModelRepository
from tests.models import User, UserRead


async def test_repository_supports_sync_engine(sync_adapter):
    repo = ModelRepository(sync_adapter, User, UserRead)
    await repo.create_item({"id": 1, "name": "Ada", "secret": "token"})
    assert (await repo.read_item_by_primary_key(1)).secret == "token"
