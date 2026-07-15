try:
    import starlette as _starlette  # noqa: F401
except ImportError as exc:
    raise ImportError("Web support requires 'ormate[web]'.") from exc

from .middleware import DBSessionMiddleware

__all__ = ["DBSessionMiddleware"]
