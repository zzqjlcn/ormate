# ormate

ormate 是一个异步 Repository 工具包，用同一套 CRUD 接口访问 SQLAlchemy、SQLModel 和 Elasticsearch。Repository 负责输入输出模型转换，Adapter 负责具体的存储操作和查询语法。

项目目前处于 `0.1.0` 阶段，API 在 `1.0` 前仍可能调整。

## 安装

需要 Python 3.13 或更高版本。核心包只依赖 SQLAlchemy：

```bash
pip install ormate
```

其他依赖按需安装：

```bash
pip install "ormate[sqlite]"
pip install "ormate[sqlmodel]"
pip install "ormate[postgresql]"
pip install "ormate[mysql]"
pip install "ormate[elasticsearch]"
pip install "ormate[web]"
```

## SQLAlchemy

```python
from pydantic import BaseModel
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from ormate import AsyncDatabase, ModelRepository, SQLAlchemyAdapter


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]


class UserCreate(BaseModel):
    id: int
    name: str


class UserRead(BaseModel):
    id: int
    name: str


db = AsyncDatabase.create("sqlite+aiosqlite:///app.db")
repository = ModelRepository(SQLAlchemyAdapter(db), User, UserRead)

async with db.engine.begin() as connection:
    await connection.run_sync(Base.metadata.create_all)

created = await repository.add(UserCreate(id=1, name="Ada"))
loaded = await repository.get(1)
updated = await repository.update_by_id(1, {"name": "Grace"})
deleted = await repository.remove_by_id(1)
```

Create 和 Update 参数可以是字典，也可以是实现了 `model_dump(exclude_unset=True)` 的 Pydantic/SQLModel 对象。传入 ReadModel 时，该模型需要提供 `model_validate()`；不传则返回存储模型。

SQLAlchemy 条件查询直接使用 SQLAlchemy 表达式：

```python
users = await repository.find(User.name.contains("Ada"), limit=20)
total = await repository.count(User.name.contains("Ada"))
```

SQLAlchemy、SQLModel 和 Elasticsearch 也可以共享结构化过滤 DSL：

```python
from ormate import and_, eq, gte, in_, not_, or_

query = and_(
    eq(Product.status, "published"),
    gte(Product.created_at, start_time),
    or_(in_(Product.category, ["guide", "reference"]), not_(eq(Product.hidden, True))),
)
items = await repository.find(query)
```

DSL 字段可以写成底层存储字段名或 SQLAlchemy/SQLModel 映射字段，例如 `eq("active", True)` 和 `eq(Product.active, True)` 等价。映射字段会在构造表达式时归一化为其存储字段名，因此 DSL AST 不持有 SQLAlchemy 对象。它提供 `eq`、`ne`、`gt`、`gte`、`lt`、`lte`、`in_`、`not_in`、`and_`、`or_` 和 `not_`。SQL JOIN、ES 全文评分、nested、geo 和聚合等能力仍使用后端原生查询。

DSL 可以复用于所有接受查询条件的 Repository 方法：

```python
# 查询与统计
books = await repository.find(and_(eq("active", True), in_("category", ["book", "guide"])))
total = await repository.count(gte("price", 100))
available = await repository.exists(not_(eq("status", "deleted")))

# 条件更新与删除
updated = await repository.update(eq("status", "draft"), {"status": "review"})
removed = await repository.remove(and_(eq("active", False), lt("updated_at", expire_at)))

# 空集合具有固定语义
await repository.find(in_("id", []))       # 恒假，返回空列表
await repository.find(not_in("id", []))   # 恒真，返回全部
```

`and_()` 恒真，`or_()` 恒假；相同类型的嵌套组合会自动展平。`and_`、`or_`、`not_` 只接受 ormate DSL 节点，不能在节点内部混入 SQLAlchemy 表达式或 ES 字典。需要后端特有能力时，将完整原生查询直接传给 Repository。

完整可运行示例：

```bash
uv run python examples/query_dsl.py
```

## ReadModel 字段投影

配置 ReadModel 后，普通读取只查询 ReadModel 验证所需的字段。`validation_alias` 用于推断存储字段，`serialization_alias` 只控制向外序列化：

```python
from pydantic import BaseModel, Field


class UserRead(BaseModel):
    display_name: str = Field(
        validation_alias="name",
        serialization_alias="displayName",
    )
```

这个模型从底层读取 `name`，执行 `model_dump(by_alias=True)` 时输出 `displayName`。普通 `alias` 同时用于验证和序列化；只有 `serialization_alias` 时仍按模型字段名读取。纯字符串 `AliasChoices` 会选择第一个存在的存储字段，`AliasPath` 因 SQL 与 ES 路径语义不同而不支持自动投影。

自动投影应用于 `find`、`find_one`、`get` 和 `get_many`。创建、更新、删除以及未配置 ReadModel 的查询仍读取完整存储对象。

## SQLModel 与事务

`SQLModelAdapter` 继承 `SQLAlchemyAdapter`，两者使用相同的 Session 和事务实现。绑定到同一个 `Database` 后，SQLAlchemy 和 SQLModel 的操作可以放在同一个事务中：

```python
audit_logs = ModelRepository(SQLAlchemyAdapter(db), AuditLog)
tasks = ModelRepository(SQLModelAdapter(db), Task)

async with db:
    await audit_logs.add({"id": 1, "message": "task created"})
    await tasks.add({"title": "publish package"})
```

作用域正常退出时提交，发生异常时回滚。同步代码可以使用 `Database` 和 `with db:`。

相关示例：

- `examples/async_sqlalchemy.py`
- `examples/sync_sqlalchemy.py`
- `examples/async_sqlmodel.py`
- `examples/shared_transaction.py`

## Elasticsearch

Elasticsearch 使用 Pydantic 文档模型，查询参数保持原生 Query DSL：

```python
from ormate import ModelRepository
from ormate.elasticsearch import ElasticsearchAdapter, ElasticsearchDocument


class ArticleDocument(ElasticsearchDocument):
    index_name = "articles"

    title: str
    content: str


adapter = ElasticsearchAdapter(
    client,
    refresh="wait_for",
    bulk_chunk_size=500,
    bulk_max_retries=3,
)
articles = ModelRepository(adapter, ArticleDocument)

created = await articles.add_many(
    [
        {"id": "quickstart", "title": "ormate", "content": "pluggable adapters"},
        {"title": "bulk", "content": "async bulk indexing"},
    ]
)
matched = await articles.find({"match": {"content": "adapters"}}, limit=10)
updated = await articles.update_by_id("quickstart", {"title": "ormate 0.1"})
deleted = await articles.remove_by_id("quickstart")
```

`add()` 和 `add_many()` 都通过官方异步 `async_streaming_bulk` 写入。默认每个 chunk 最多 500 条、100 MiB，对 HTTP 429 最多重试 3 次并使用异步指数退避。可通过以下 Adapter 参数调整：

- `bulk_chunk_size`
- `bulk_max_chunk_bytes`
- `bulk_max_retries`
- `bulk_initial_backoff`
- `bulk_max_backoff`

设置 `refresh=True` 或 `refresh="wait_for"` 时，所有 chunk 完成后只 refresh 一次。单条文档失败时，其余成功项不会回滚，方法会在处理完整批次后抛出 Elasticsearch 官方 `BulkIndexError`，错误明细位于异常的 `errors` 属性。

完整的索引初始化、CRUD、计数、聚合和客户端关闭示例在 `examples/elasticsearch.py`：

```bash
ELASTICSEARCH_URL=http://localhost:9200 uv run python examples/elasticsearch.py
```

全文检索和聚合等 ES 专属操作直接通过 `ElasticsearchAdapter` 调用。Elasticsearch 不参与 SQL 事务；SQL 与 ES 双写需要使用 outbox、消息队列或补偿机制。

## Repository 和 Adapter

`ModelRepository` 提供以下通用操作：

- `add`、`add_many`
- `find`、`find_one`、`get`、`get_many`
- `update`、`update_by_id`、`update_many`
- `remove`、`remove_by_id`、`remove_many`
- `count`、`exists`、`limit`、`offset`
- 后端原生命令执行

SQLAlchemy/SQLModel 额外支持复合主键。后端特有的能力不放进通用协议，例如 SQL JOIN 和 ES 聚合分别留在对应 Adapter 中。

实现 `StorageAdapter` 协议可以接入其他存储：

```python
repository = ModelRepository(custom_adapter, CustomModel, CustomRead)
```

Adapter 负责持久化、查询、主键条件和存储名称。Repository 负责输入转换、`encode_for_storage()`、`decode_from_storage()` 和 ReadModel 构造。

ormate 不定义 `id`、`created_at`、`updated_at` 等业务字段。SQLAlchemy/SQLModel 继续使用 `__tablename__`，Elasticsearch 使用 `index_name`，统一名称可以从 Repository 获取：

```python
repository.storage_name
```

`ElasticsearchDocument.id` 只用于映射 Elasticsearch `_id`。

## Web 中间件

```python
from ormate.web import DBSessionMiddleware

app.add_middleware(
    DBSessionMiddleware,
    db=db,
    rollback_on_http_error=True,
)
```

中间件接受 `AsyncDatabase` 或 `AsyncEngine`，为每个 HTTP/WebSocket 请求建立独立会话作用域。

## 当前限制

- PostgreSQL、MySQL 和真实 Elasticsearch 集群尚未加入自动化集成测试。
- Elasticsearch 条件批量更新和删除受 `default_size` 限制，默认最多处理 1000 个匹配文档。
- ES mapping 迁移、PIT/search_after 和乐观并发控制尚未实现。
- 不提供 SQL 与 Elasticsearch 之间的分布式事务。

## 路线图

`0.1.x` 用于完成首次 PyPI 发布，当前还需要经过 TestPyPI 安装验证。

`0.2` 主要完善 Elasticsearch：PIT/search_after、索引 mapping 管理、并发冲突处理和真实集群测试。

`0.3` 主要完善关系型数据库：PostgreSQL/MySQL 测试矩阵、分页结果类型、显式 savepoint API 和批量性能优化。

后续会补充 Adapter 契约测试工具，并评估 MongoDB、RedisJSON 以及 SQL 到 ES 的 outbox 示例。到 `1.0` 前会冻结公共 API，补齐迁移指南和性能基准。

路线图只表示开发方向，不承诺具体发布日期。

## 开发

```bash
uv sync --all-extras
uv run ruff check .
uv run mypy
uv run pytest
uv build
uv run twine check dist/*
```

发布步骤见 `docs/publishing.md`。

## License

[MIT License](LICENSE)
