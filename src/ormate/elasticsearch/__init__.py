try:
    import elasticsearch as _elasticsearch  # noqa: F401
    import pydantic as _pydantic  # noqa: F401
except ImportError as exc:
    raise ImportError("Elasticsearch support requires 'ormate[elasticsearch]'.") from exc

from ormate.adapters.elasticsearch import ElasticsearchAdapter

from .document import ElasticsearchDocument

__all__ = ["ElasticsearchAdapter", "ElasticsearchDocument"]

