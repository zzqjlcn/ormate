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

created = await repository.create_item(UserCreate(id=1, name="Ada"))
loaded = await repository.read_item_by_primary_key(1)
updated = await repository.update_item_by_primary_key(1, {"name": "Grace"})
deleted = await repository.delete_item_by_primary_key(1)
```

Create 和 Update 参数可以是字典，也可以是实现了 `model_dump(exclude_unset=True)` 的 Pydantic/SQLModel 对象。传入 ReadModel 时，该模型需要提供 `model_validate()`；不传则返回存储模型。

SQLAlchemy 条件查询直接使用 SQLAlchemy 表达式：

```python
users = await repository.read_items(User.name.contains("Ada"), limit=20)
total = await repository.count(User.name.contains("Ada"))
```

## SQLModel 与事务

`SQLModelAdapter` 继承 `SQLAlchemyAdapter`，两者使用相同的 Session 和事务实现。绑定到同一个 `Database` 后，SQLAlchemy 和 SQLModel 的操作可以放在同一个事务中：

```python
audit_logs = ModelRepository(SQLAlchemyAdapter(db), AuditLog)
tasks = ModelRepository(SQLModelAdapter(db), Task)

async with db:
    await audit_logs.create_item({"id": 1, "message": "task created"})
    await tasks.create_item({"title": "publish package"})
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


adapter = ElasticsearchAdapter(client, refresh="wait_for")
articles = ModelRepository(adapter, ArticleDocument)

created = await articles.create_item(
    {"id": "quickstart", "title": "ormate", "content": "pluggable adapters"}
)
matched = await articles.read_items({"match": {"content": "adapters"}}, limit=10)
updated = await articles.update_item_by_primary_key("quickstart", {"title": "ormate 0.1"})
deleted = await articles.delete_item_by_primary_key("quickstart")
```

完整的索引初始化、CRUD、计数、聚合和客户端关闭示例在 `examples/elasticsearch.py`：

```bash
ELASTICSEARCH_URL=http://localhost:9200 uv run python examples/elasticsearch.py
```

全文检索和聚合等 ES 专属操作直接通过 `ElasticsearchAdapter` 调用。Elasticsearch 不参与 SQL 事务；SQL 与 ES 双写需要使用 outbox、消息队列或补偿机制。

## Repository 和 Adapter

`ModelRepository` 提供以下通用操作：

- 单项和批量创建
- 条件查询、主键查询和批量主键查询
- 条件更新和删除
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
- ES mapping 迁移、bulk、PIT/search_after 和乐观并发控制尚未实现。
- 不提供 SQL 与 Elasticsearch 之间的分布式事务。

## 路线图

`0.1.x` 用于完成首次 PyPI 发布，当前还需要经过 TestPyPI 安装验证。

`0.2` 主要完善 Elasticsearch：bulk 写入、PIT/search_after、索引 mapping 管理、并发冲突处理和真实集群测试。

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

