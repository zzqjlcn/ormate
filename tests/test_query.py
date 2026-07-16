import pytest
from sqlalchemy import select

from ormate import ModelRepository, and_, eq, gt, in_, ne, not_, not_in, or_
from ormate.query import BooleanExpression, Constant
from tests.models import User, UserRead


async def test_structured_query_works_with_sqlalchemy(async_adapter):
    repository = ModelRepository(async_adapter, User, UserRead)
    await repository.add_many(
        [
            {"id": 1, "name": "Ada", "secret": "a"},
            {"id": 2, "name": "Grace", "secret": "b"},
            {"id": 3, "name": "Linus", "secret": "c"},
        ]
    )

    query = and_(gt(User.id, 1), or_(eq(User.name, "Grace"), eq(User.name, "Linus")), not_(eq(User.id, 3)))
    assert [user.id for user in await repository.find(query)] == [2]
    assert await repository.count(in_("id", [1, 3])) == 2
    assert await repository.exists(ne("name", "Nobody"))
    assert await repository.count(not_in("id", [])) == 3
    assert await repository.count(in_("id", [])) == 0


async def test_native_sqlalchemy_query_and_statement_remain_supported(async_adapter):
    repository = ModelRepository(async_adapter, User, UserRead)
    await repository.add({"id": 1, "name": "Ada", "secret": "a"})
    statement = select(User).order_by(User.id.desc())
    assert (await repository.find(User.name == "Ada", statement=statement))[0].id == 1


def test_boolean_helpers_flatten_and_reject_native_expressions():
    expression = and_(eq("id", 1), and_(eq("name", "Ada"), eq("secret", "a")))
    assert isinstance(expression, BooleanExpression)
    assert len(expression.expressions) == 3
    assert and_() == Constant(True)
    assert or_() == Constant(False)
    with pytest.raises(TypeError, match="only accept ormate"):
        and_(User.id == 1)  # type: ignore[arg-type]


def test_mapped_field_is_normalized_to_storage_field_name():
    expression = eq(User.name, "Ada")
    assert expression == eq("name", "Ada")
    with pytest.raises(TypeError, match="mapped field"):
        eq(object(), "Ada")  # type: ignore[arg-type]


async def test_unknown_structured_query_field_is_clear(async_adapter):
    repository = ModelRepository(async_adapter, User, UserRead)
    with pytest.raises(ValueError, match="Unknown query field 'missing'.*User"):
        await repository.find(eq("missing", 1))
