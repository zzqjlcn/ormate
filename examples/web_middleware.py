from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from ormate import AsyncDatabase
from ormate.web import DBSessionMiddleware

db = AsyncDatabase.create("sqlite+aiosqlite:///app.db")


async def health(request):
    return JSONResponse({"status": "ok"})


app = Starlette(routes=[Route("/health", health)])
app.add_middleware(DBSessionMiddleware, db=db)
