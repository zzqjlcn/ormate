from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict


class ElasticsearchDocument(BaseModel):
    """Base model for Elasticsearch `_source` documents."""

    model_config = ConfigDict(extra="allow")

    index_name: ClassVar[str]
    id: str | None = None

    def document_source(self) -> dict[str, Any]:
        return self.model_dump(exclude={"id"}, exclude_none=True)

    @classmethod
    def from_hit(cls, hit: dict[str, Any]) -> "ElasticsearchDocument":
        return cls.model_validate({"id": hit.get("_id"), **hit.get("_source", {})})

