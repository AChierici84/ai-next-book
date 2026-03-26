from fastapi import FastAPI

from app.chroma_store import ChromaBookStore
from app.config import settings
from app.models import QueryRequest

app = FastAPI(title=settings.app_name)
store = ChromaBookStore()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/stats")
def stats() -> dict[str, int]:
    return {"documents": store.count()}


@app.post("/query")
def query_books(payload: QueryRequest):
    results = store.query(
        text=payload.query,
        limit=payload.limit,
        year_from=payload.year_from,
        year_to=payload.year_to,
        material_type=payload.material_type,
    )
    return {
        "query": payload.query,
        "count": len(results),
        "results": [result.model_dump() for result in results],
    }
