from collections.abc import Mapping, Sequence
from typing import Any

from ormate.projection import ReadField
from ormate.query import BooleanExpression, Comparison, Constant, NotExpression, QueryExpression, SetComparison


class ElasticsearchAdapter:
    """Async Elasticsearch adapter using native Query DSL dictionaries."""

    def __init__(self, client: Any, *, refresh: bool | str = False, default_size: int = 1000) -> None:
        if default_size < 1:
            raise ValueError("default_size must be greater than zero")
        self.client = client
        self.refresh = refresh
        self.default_size = default_size

    def storage_name(self, model: type[Any]) -> str:
        index_name = getattr(model, "index_name", None)
        if not isinstance(index_name, str) or not index_name:
            raise TypeError("Elasticsearch document model must define a non-empty index_name")
        return index_name

    def _document(self, model: type[Any], values: Mapping[str, Any]) -> Any:
        validator = getattr(model, "model_validate", None)
        if not callable(validator):
            raise TypeError("Elasticsearch document model must provide model_validate()")
        return validator(values)

    def _source(self, document: Any) -> dict[str, Any]:
        serializer = getattr(document, "document_source", None)
        if not callable(serializer):
            raise TypeError("Elasticsearch document must provide document_source()")
        return dict(serializer())

    def _from_hit(self, model: type[Any], hit: Mapping[str, Any]) -> Any:
        factory = getattr(model, "from_hit", None)
        if not callable(factory):
            raise TypeError("Elasticsearch document model must provide from_hit()")
        return factory(dict(hit))

    def primary_key_query(self, model: type[Any], primary_key: Any) -> dict[str, Any]:
        return {"ids": {"values": [str(primary_key)]}}

    def primary_keys_query(self, model: type[Any], primary_keys: Sequence[Any]) -> dict[str, Any]:
        return {"ids": {"values": [str(primary_key) for primary_key in primary_keys]}}

    def _available_fields(self, model: type[Any]) -> set[str]:
        model_fields = getattr(model, "model_fields", None)
        return set(model_fields) if isinstance(model_fields, Mapping) else set()

    def _projection_fields(self, model: type[Any], projection: Sequence[ReadField]) -> list[str]:
        available = self._available_fields(model)
        fields: list[str] = []
        for read_field in projection:
            storage_field = next((name for name in read_field.candidates if name in available), None)
            if storage_field is None:
                candidates = ", ".join(repr(name) for name in read_field.candidates)
                raise ValueError(
                    f"ReadModel field {read_field.name!r} resolved to [{candidates}], but none exists "
                    f"on storage model {model.__name__}"
                )
            if storage_field != "id":
                fields.append(storage_field)
        return fields

    def _query_field(self, model: type[Any], field: str) -> str:
        if field not in self._available_fields(model):
            raise ValueError(f"Unknown query field {field!r} for storage model {model.__name__}")
        return field

    def _compile_query(self, model: type[Any], query: Any) -> Any:
        if not isinstance(query, QueryExpression):
            return query
        if isinstance(query, Constant):
            return {"match_all": {}} if query.value else {"match_none": {}}
        if isinstance(query, Comparison):
            field = self._query_field(model, query.field)
            if query.operator == "eq":
                return {"term": {field: query.value}}
            if query.operator == "ne":
                return {"bool": {"must_not": [{"term": {field: query.value}}]}}
            return {"range": {field: {query.operator: query.value}}}
        if isinstance(query, SetComparison):
            field = self._query_field(model, query.field)
            clause = {"terms": {field: list(query.values)}}
            return {"bool": {"must_not": [clause]}} if query.negated else clause
        if isinstance(query, BooleanExpression):
            clauses = [self._compile_query(model, expression) for expression in query.expressions]
            if query.operator == "and":
                return {"bool": {"filter": clauses}}
            return {"bool": {"should": clauses, "minimum_should_match": 1}}
        if isinstance(query, NotExpression):
            return {"bool": {"must_not": [self._compile_query(model, query.expression)]}}
        raise TypeError(f"Unsupported query expression: {type(query).__name__}")

    async def add(self, model: type[Any], items: Sequence[Mapping[str, Any]]) -> list[Any]:
        index_name = self.storage_name(model)
        results = []
        for values in items:
            document = self._document(model, values)
            response = await self.client.index(
                index=index_name,
                id=getattr(document, "id", None),
                document=self._source(document),
                refresh=self.refresh,
            )
            result_values = {"id": response.get("_id"), **self._source(document)}
            results.append(self._document(model, result_values))
        return results

    async def find(
        self,
        model: type[Any],
        query: Any = None,
        *,
        limit: int | None = None,
        offset: int | None = None,
        statement: Any = None,
        projection: Sequence[ReadField] | None = None,
    ) -> list[Any]:
        if statement is not None and not isinstance(statement, Mapping):
            raise TypeError("Elasticsearch statement must be a search keyword mapping")
        search_options = dict(statement or {})
        compiled_query = self._compile_query(model, query) if query is not None else {"match_all": {}}
        search_options.setdefault("query", compiled_query)
        search_options.setdefault("from_", offset or 0)
        search_options.setdefault("size", limit if limit is not None else self.default_size)
        if projection is not None:
            search_options.setdefault("source_includes", self._projection_fields(model, projection))
        response = await self.client.search(index=self.storage_name(model), **search_options)
        if projection is not None:
            return [{"id": hit.get("_id"), **hit.get("_source", {})} for hit in response["hits"]["hits"]]
        return [self._from_hit(model, hit) for hit in response["hits"]["hits"]]

    async def update(self, model: type[Any], query: Any, values: Mapping[str, Any]) -> list[Any]:
        documents = await self.find(model, query)
        index_name = self.storage_name(model)
        results = []
        for document in documents:
            document_id = getattr(document, "id", None)
            if document_id is None:
                continue
            await self.client.update(
                index=index_name,
                id=document_id,
                doc=dict(values),
                refresh=self.refresh,
            )
            merged = {"id": document_id, **self._source(document), **values}
            results.append(self._document(model, merged))
        return results

    async def remove(self, model: type[Any], query: Any) -> list[Any]:
        documents = await self.find(model, query)
        index_name = self.storage_name(model)
        for document in documents:
            document_id = getattr(document, "id", None)
            if document_id is not None:
                await self.client.delete(index=index_name, id=document_id, refresh=self.refresh)
        return documents

    async def count(self, model: type[Any], query: Any = None, *, statement: Any = None) -> int:
        if statement is not None:
            raise TypeError("Elasticsearch count does not accept a statement; pass Query DSL through query")
        compiled = self._compile_query(model, query) if query is not None else {"match_all": {}}
        response = await self.client.count(index=self.storage_name(model), query=compiled)
        return int(response["count"])

    async def exists(self, model: type[Any], query: Any = None) -> bool:
        return await self.count(model, query) > 0

    async def execute(self, statement: Any, params: Any = None, **kwargs: Any) -> Any:
        if not isinstance(statement, str):
            raise TypeError("Elasticsearch native execute statement must be a client method name")
        method = getattr(self.client, statement, None)
        if not callable(method):
            raise ValueError(f"Unknown Elasticsearch client method: {statement}")
        call_options = dict(params or {})
        call_options.update(kwargs)
        return await method(**call_options)

    async def search(self, model: type[Any], query: Mapping[str, Any], **kwargs: Any) -> Any:
        return await self.client.search(index=self.storage_name(model), query=query, **kwargs)

    async def aggregate(self, model: type[Any], aggregations: Mapping[str, Any], query: Any = None) -> Any:
        return await self.client.search(
            index=self.storage_name(model),
            query=query or {"match_all": {}},
            aggregations=aggregations,
            size=0,
        )
