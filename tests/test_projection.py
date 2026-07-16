import pytest
from pydantic import AliasChoices, AliasPath, BaseModel, Field

from ormate import ModelRepository
from ormate.projection import read_model_fields
from tests.models import User


class AliasedUserRead(BaseModel):
    identifier: int = Field(alias="id")
    display_name: str = Field(validation_alias="name", serialization_alias="displayName")
    secret: str = Field(serialization_alias="credential")


class ChoiceUserRead(BaseModel):
    identifier: int = Field(validation_alias=AliasChoices("missing_id", "id"))
    name: str


async def test_read_model_validation_aliases_drive_sql_projection(async_adapter):
    repository = ModelRepository(async_adapter, User, AliasedUserRead)
    created = await repository.add({"id": 1, "name": "Ada", "secret": "token"})
    assert created.model_dump(by_alias=True) == {"id": 1, "displayName": "Ada", "credential": "nekot"}

    raw = await async_adapter.find(User, projection=read_model_fields(AliasedUserRead))
    assert set(raw[0]) == {"id", "name", "secret"}
    found = await repository.get(1)
    assert found.identifier == 1
    assert found.display_name == "Ada"


async def test_alias_choices_select_first_existing_storage_field(async_adapter):
    repository = ModelRepository(async_adapter, User, ChoiceUserRead)
    await repository.add({"id": 1, "name": "Ada", "secret": "token"})
    assert (await repository.get(1)).identifier == 1


async def test_unknown_projection_field_reports_read_and_storage_models(async_adapter):
    class InvalidRead(BaseModel):
        absent: str

    repository = ModelRepository(async_adapter, User, InvalidRead)
    with pytest.raises(ValueError, match="ReadModel field 'absent'.*storage model User"):
        await repository.find()


async def test_alias_choices_without_storage_match_reports_candidates(async_adapter):
    class InvalidChoiceRead(BaseModel):
        value: str = Field(validation_alias=AliasChoices("first_missing", "second_missing"))

    repository = ModelRepository(async_adapter, User, InvalidChoiceRead)
    with pytest.raises(ValueError, match="first_missing.*second_missing.*storage model User"):
        await repository.find()


def test_alias_path_is_rejected_during_repository_construction(async_adapter):
    class PathRead(BaseModel):
        name: str = Field(validation_alias=AliasPath("profile", "name"))

    with pytest.raises(TypeError, match="AliasPath"):
        ModelRepository(async_adapter, User, PathRead)


async def test_repository_without_read_model_returns_full_entity(async_adapter):
    repository = ModelRepository(async_adapter, User)
    await repository.add({"id": 1, "name": "Ada", "secret": "token"})
    found = await repository.get(1)
    assert isinstance(found, User)
    assert found.secret == "nekot"
