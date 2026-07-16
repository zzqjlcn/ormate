from ormate import ModelRepository
from tests.models import User, UserRead


async def test_repository_supports_sync_engine(sync_adapter):
    repo = ModelRepository(sync_adapter, User, UserRead)
    await repo.add({"id": 1, "name": "Ada", "secret": "token"})
    assert (await repo.get(1)).secret == "token"
