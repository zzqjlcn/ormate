import asyncio
import os

from elasticsearch import AsyncElasticsearch

from ormate import ModelRepository
from ormate.elasticsearch import ElasticsearchAdapter, ElasticsearchDocument


class ArticleDocument(ElasticsearchDocument):
    index_name = "articles"

    title: str
    content: str
    category: str


async def initialize_index(client: AsyncElasticsearch) -> None:
    if await client.indices.exists(index=ArticleDocument.index_name):
        return
    await client.indices.create(
        index=ArticleDocument.index_name,
        mappings={
            "properties": {
                "title": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "content": {"type": "text"},
                "category": {"type": "keyword"},
            }
        },
    )


async def main() -> None:
    client = AsyncElasticsearch(os.getenv("ELASTICSEARCH_URL", "http://localhost:9200"))
    adapter = ElasticsearchAdapter(client, refresh="wait_for")
    articles = ModelRepository(adapter, ArticleDocument)

    try:
        await initialize_index(client)

        # Create：指定 id 可重复运行；不指定时由 Elasticsearch 生成。
        created = await articles.create_item(
            {
                "id": "ormate-quickstart",
                "title": "Ormate quickstart",
                "content": "Use one repository API with pluggable storage adapters.",
                "category": "python",
            }
        )
        print("created:", created)

        # Read：按主键读取，以及使用 Elasticsearch Query DSL 条件查询。
        article = await articles.read_item_by_primary_key("ormate-quickstart")
        print("read by id:", article)

        matched = await articles.read_items(
            {"match": {"content": "storage adapters"}},
            limit=10,
        )
        print("matched:", matched)

        # Update：部分更新，不会覆盖未提供字段。
        updated = await articles.update_item_by_primary_key(
            "ormate-quickstart",
            {"title": "Ormate Elasticsearch quickstart"},
        )
        print("updated:", updated)

        print("count:", await articles.count({"term": {"category": "python"}}))
        print("exists:", await articles.exists({"ids": {"values": ["ormate-quickstart"]}}))

        # Elasticsearch 专属能力直接通过 Adapter 使用。
        aggregation = await adapter.aggregate(
            ArticleDocument,
            {"categories": {"terms": {"field": "category"}}},
        )
        print("aggregation:", aggregation.get("aggregations", {}))

        # Delete：返回删除前的文档；再次读取得到 None。
        deleted = await articles.delete_item_by_primary_key("ormate-quickstart")
        print("deleted:", deleted)
        print("after delete:", await articles.read_item_by_primary_key("ormate-quickstart"))
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())

