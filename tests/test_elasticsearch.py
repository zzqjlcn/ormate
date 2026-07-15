from typing import Any

from pydantic import BaseModel

from ormate import ModelRepository
from ormate.elasticsearch import ElasticsearchAdapter, ElasticsearchDocument


class KnowledgeDocument(ElasticsearchDocument):
    index_name = "knowledge"

    title: str
    content: str


class KnowledgeRead(BaseModel):
    id: str
    title: str
    content: str


class FakeElasticsearch:
    def __init__(self) -> None:
        self.documents: dict[str, dict[str, Any]] = {}

    async def index(self, *, id=None, document, **kwargs):
        document_id = str(id or len(self.documents) + 1)
        self.documents[document_id] = dict(document)
        return {"_id": document_id}

    async def search(self, *, query, from_=0, size=10, **kwargs):
        items = list(self.documents.items())
        if "ids" in query:
            ids = set(query["ids"]["values"])
            items = [(key, value) for key, value in items if key in ids]
        elif "term" in query:
            field, expected = next(iter(query["term"].items()))
            items = [(key, value) for key, value in items if value.get(field) == expected]
        hits = [{"_id": key, "_source": value} for key, value in items[from_ : from_ + size]]
        return {"hits": {"hits": hits}, "aggregations": {}}

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

    created = await repository.create_item({"title": "ORM", "content": "adapter"})
    assert created.id == "1"
    assert (await repository.read_item_by_primary_key("1")).title == "ORM"
    assert await repository.exists({"term": {"title": "ORM"}})

    updated = await repository.update_item_by_primary_key("1", {"title": "Ormate"})
    assert updated.title == "Ormate"
    assert await repository.count() == 1
    assert await repository.execute("ping") is True

    deleted = await repository.delete_item_by_primary_key("1")
    assert deleted.id == "1"
    assert await repository.count() == 0
