from typing import Literal

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
    query_year: int

    def to_document_text(self) -> str:
        parts = [
            f"Titolo: {self.title}",
            f"Autore: {self.author}" if self.author else None,
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
        }


class QueryRequest(BaseModel):
    query: str
    limit: int = Field(default=5, ge=1, le=20)
    year_from: int | None = None
    year_to: int | None = None
    material_type: str | None = None


class QueryResult(BaseModel):
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
    score: float


class IngestSummary(BaseModel):
    status: Literal["ok"] = "ok"
    years_processed: int
    documents_upserted: int
