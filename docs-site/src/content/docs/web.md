---
title: 一个 HTTP 请求，一个会话作用域
description: 使用 ASGI 中间件管理请求事务，并在后台任务开始前正确结束请求 Session。
kicker: WEB MIDDLEWARE
order: 9
---

安装 Web extra：

```bash
pip install "ormate[web]"
```

## 添加中间件

```python
from ormate.web import DBSessionMiddleware

app.add_middleware(
    DBSessionMiddleware,
    db=db,
    rollback_on_http_error=True,
)
```

中间件接受 `AsyncDatabase` 或 `AsyncEngine`，只为 HTTP 请求建立会话作用域。

最终响应体发送后，中间件提交或回滚并关闭 Session。因此 Starlette/FastAPI `BackgroundTasks` 不会继续持有请求事务。

## WebSocket

WebSocket 不由中间件管理，应按每条消息或每次业务操作创建短事务。

```python
async for message in websocket.iter_text():
    async with db:
        await messages.add({"content": message})
```

手动创建、跨框架传递或延迟启动的后台任务仍可在入口使用 `detached()`。
