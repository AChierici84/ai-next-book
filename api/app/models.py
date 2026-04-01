from pydantic import BaseModel, Field


class BookDocument(BaseModel):
    id: str
    title: str
    author: str | None = None
    year: int | None = None
    material_type: str | None = None
    summary: str | None = None
    libraries: list[str] = Field(default_factory=list)
    available_copies: int | None = None
    total_copies: int | None = None
    source_url: str
    cover_url: str | None = None
    query_year: int

    def to_document_text(self) -> str:
        parts = [
            f"Titolo: {self.title}",
            f"Autore: {self.author}" if self.author else None,
            f"Anno: {self.year}" if self.year else None,
            f"Riassunto: {self.summary}" if self.summary else None,
        ]
        return "\n".join(part for part in parts if part)

    def to_metadata(self) -> dict[str, str | int | float | bool]:
        return {
            "title": self.title,
            "author": self.author or "",
            "year": self.year or 0,
            "material_type": self.material_type or "",
            "query_year": self.query_year,
            "available_copies": self.available_copies or 0,
            "total_copies": self.total_copies or 0,
            "libraries": " | ".join(self.libraries),
            "source_url": self.source_url,
            "cover_url": self.cover_url or "",
        }


class QueryRequest(BaseModel):
    query: str
    limit: int = Field(default=5, ge=1, le=20)
    year_from: int | None = None
    year_to: int | None = None
    material_type: str | None = None


class HybridQueryRequest(QueryRequest):
    llm_suggestions: int = Field(default=20, ge=5, le=50)


class OpacLookupRequest(BaseModel):
    resource_id: str | None = None
    source_url: str | None = None


class LlmSuggestion(BaseModel):
    title: str
    author: str | None = None
