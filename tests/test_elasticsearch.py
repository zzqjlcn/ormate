from typing import Any

import pytest
from pydantic import BaseModel, Field

from ormate import ModelRepository, and_, eq, gt, not_, or_
from ormate.elasticsearch import ElasticsearchAdapter, ElasticsearchDocument


class KnowledgeDocument(ElasticsearchDocument):
    index_name = "knowledge"

    title: str
    content: str


class KnowledgeRead(BaseModel):
    id: str
    title: str
    content: str


class KnowledgeAliasRead(BaseModel):
    id: str
    heading: str = Field(validation_alias="title", serialization_alias="headingText")


class FakeElasticsearch:
    def __init__(self) -> None:
        self.documents: dict[str, dict[str, Any]] = {}
        self.last_source_includes = None

    async def index(self, *, id=None, document, **kwargs):
        document_id = str(id or len(self.documents) + 1)
        self.documents[document_id] = dict(document)
        return {"_id": document_id}

    async def search(self, *, query, from_=0, size=10, source_includes=None, **kwargs):
        self.last_source_includes = source_includes
        items = list(self.documents.items())
        items = [(key, value) for key, value in items if self._matches(key, value, query)]
        hits = []
        for key, value in items[from_ : from_ + size]:
            source = (
                value
                if source_includes is None
                else {field: value[field] for field in source_includes if field in value}
            )
            hits.append({"_id": key, "_source": source})
        return {"hits": {"hits": hits}, "aggregations": {}}

    def _matches(self, key, value, query):
        if "match_all" in query:
            return True
        if "match_none" in query:
            return False
        if "ids" in query:
            return key in set(query["ids"]["values"])
        if "term" in query:
            field, expected = next(iter(query["term"].items()))
            return value.get(field) == expected
        if "terms" in query:
            field, expected = next(iter(query["terms"].items()))
            return value.get(field) in expected
        if "range" in query:
            field, condition = next(iter(query["range"].items()))
            actual = value.get(field)
            return all(
                {
                    "gt": actual > expected,
                    "gte": actual >= expected,
                    "lt": actual < expected,
                    "lte": actual <= expected,
                }[operator]
                for operator, expected in condition.items()
            )
        boolean = query.get("bool")
        if boolean is not None:
            filters = boolean.get("filter", [])
            must_not = boolean.get("must_not", [])
            should = boolean.get("should", [])
            return (
                all(self._matches(key, value, clause) for clause in filters)
                and not any(self._matches(key, value, clause) for clause in must_not)
                and (not should or sum(self._matches(key, value, clause) for clause in should) >= 1)
            )
        return True

    async def update(self, *, id, doc, **kwargs):
        self.documents[str(id)].update(doc)
        return {"_id": str(id)}

    async def delete(self, *, id, **kwargs):
        self.documents.pop(str(id))
        return {"_id": str(id)}

    async def count(self, *, query, **kwargs):
        response = await self.search(query=query, size=10_000)
        return {"count": len(response["hits"]["hits"])}

    async def ping(self):
        return True


async def test_elasticsearch_adapter_uses_same_repository_api():
    adapter = ElasticsearchAdapter(FakeElasticsearch())
    repository = ModelRepository(adapter, KnowledgeDocument, KnowledgeRead)
    assert repository.storage_name == "knowledge"

    created = await repository.add({"title": "ORM", "content": "adapter"})
    assert created.id == "1"
    assert (await repository.get("1")).title == "ORM"
    assert await repository.exists({"term": {"title": "ORM"}})

    updated = await repository.update_by_id("1", {"title": "Ormate"})
    assert updated.title == "Ormate"
    assert await repository.count() == 1
    assert await repository.execute("ping") is True

    deleted = await repository.remove_by_id("1")
    assert deleted.id == "1"
    assert await repository.count() == 0


async def test_elasticsearch_projection_aliases_and_structured_query():
    client = FakeElasticsearch()
    repository = ModelRepository(ElasticsearchAdapter(client), KnowledgeDocument, KnowledgeAliasRead)
    await repository.add_many(
        [
            {"id": "1", "title": "ORM", "content": "adapter"},
            {"id": "2", "title": "SQL", "content": "database"},
        ]
    )

    query = and_(gt("title", "A"), or_(eq("title", "ORM"), eq("title", "SQL")), not_(eq("title", "SQL")))
    found = await repository.find(query)
    assert [item.heading for item in found] == ["ORM"]
    assert client.last_source_includes == ["title"]
    assert found[0].model_dump(by_alias=True)["headingText"] == "ORM"

    with pytest.raises(ValueError, match="Unknown query field 'missing'.*KnowledgeDocument"):
        await repository.find(eq("missing", "value"))
