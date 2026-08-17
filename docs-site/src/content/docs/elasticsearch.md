---
title: 批量写入，保留原生 Query DSL
description: 使用 Pydantic 文档模型、异步 streaming bulk 和 Elasticsearch 原生查询能力。
kicker: ELASTICSEARCH
order: 8
---

Elasticsearch 使用 Pydantic 文档模型，查询参数保持原生 Query DSL。通用结构化 DSL 也可以用于普通过滤。

## 文档模型

```python
from ormate import ModelRepository
from ormate.elasticsearch import ElasticsearchAdapter, ElasticsearchDocument


class ArticleDocument(ElasticsearchDocument):
    index_name = "articles"

    title: str
    content: str
```

`ElasticsearchDocument.id` 只用于映射 Elasticsearch `_id`。

## Streaming bulk

```python
adapter = ElasticsearchAdapter(
    client,
    refresh="wait_for",
    bulk_chunk_size=500,
    bulk_max_retries=3,
)
articles = ModelRepository(adapter, ArticleDocument)

await articles.add_many(documents)
```

默认行为：

- 每个 chunk 最多 500 条；
- 每个 chunk 最大 100 MiB；
- HTTP 429 最多重试 3 次；
- 使用异步指数退避；
- `refresh=True` 或 `refresh="wait_for"` 时，所有 chunk 完成后只 refresh 一次。

单条文档失败时，其余成功项不会回滚。方法处理完整个批次后抛出官方 `BulkIndexError`，错误明细位于 `errors` 属性。

## 原生查询

```python
matched = await articles.find(
    {"match": {"content": "adapters"}},
    limit=10,
)
```

全文评分、nested、geo 和聚合应继续使用 Elasticsearch 原生能力。

> Elasticsearch 不参与 SQL 事务。SQL 与 ES 双写应使用 outbox、消息队列或补偿机制。
