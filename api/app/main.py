import logging
from time import perf_counter

from fastapi import FastAPI
from fastapi import Response

from app.config import settings
from app.llm_recommender import suggest_books_from_llm
from app.models import HybridQueryRequest, OpacLookupRequest, QueryRequest
from app.opac_scraper import OpacScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)


@app.get("/")
def root() -> dict[str, object]:
    return {
        "service": settings.app_name,
        "status": "ok",
        "mode": "opac_live",
        "endpoints": ["/health", "/stats", "/query", "/query/hybrid", "/opac/lookup"],
    }


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)


def _passes_filters(
    book: dict,
    *,
    year_from: int | None,
    year_to: int | None,
    material_type: str | None,
) -> bool:
    book_year = book.get("year") or 0
    if year_from is not None and book_year < year_from:
        return False
    if year_to is not None and book_year > year_to:
        return False

    if material_type:
        required = material_type.strip().lower()
        current = str(book.get("material_type") or "").lower().strip()
        # Do not discard records when OPAC page doesn't expose material type reliably.
        if current and required not in current:
            return False

    return True


def _book_to_result(book) -> dict:
    return {
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "year": book.year,
        "material_type": book.material_type,
        "summary": book.summary,
        "cover_url": book.cover_url,
        "libraries": book.libraries,
        "available_copies": book.available_copies,
        "total_copies": book.total_copies,
        "source_url": book.source_url,
        "score": 1.0,
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/stats")
def stats() -> dict[str, int]:
    # OPAC-only mode: no local vector index involved.
    return {"documents": 0}


@app.post("/opac/lookup")
def opac_lookup(payload: OpacLookupRequest):
    logger.info(
        "/opac/lookup received | resource_id=%r | source_url=%r",
        payload.resource_id,
        payload.source_url,
    )

    scraper = OpacScraper(logger=logger)
    try:
        book = scraper.fetch_resource_live(
            resource_id=payload.resource_id,
            source_url=payload.source_url,
        )
    finally:
        scraper.close()

    if not book:
        logger.info("/opac/lookup completed | exists=false")
        return {"exists": False, "source": "opac_realtime", "book": None}

    logger.info("/opac/lookup completed | exists=true | id=%s", book.id)
    return {
        "exists": True,
        "source": "opac_realtime",
        "book": book.model_dump(),
    }


@app.post("/query")
def query_books(payload: QueryRequest):
    logger.info(
        "/query received | q=%r | limit=%s | year_from=%s | year_to=%s | material_type=%r",
        payload.query,
        payload.limit,
        payload.year_from,
        payload.year_to,
        payload.material_type,
    )
    started = perf_counter()
    opac_results = []
    try:
        scraper = OpacScraper(logger=logger)
        try:
            candidates = scraper.search_books_live(
                title=payload.query,
                author=None,
                limit=payload.limit,
                material_type=payload.material_type,
            )
            for book in candidates:
                if not _passes_filters(
                    {
                        "year": book.year,
                        "material_type": book.material_type,
                    },
                    year_from=payload.year_from,
                    year_to=payload.year_to,
                    material_type=payload.material_type,
                ):
                    continue

                opac_results.append(_book_to_result(book))
                if len(opac_results) >= payload.limit:
                    break
        finally:
            scraper.close()
    except Exception as exc:
        logger.warning("/query opac lookup failed | error=%s", exc)

    elapsed_ms = int((perf_counter() - started) * 1000)
    logger.info("/query completed | source=opac_live | count=%s | elapsed_ms=%s", len(opac_results), elapsed_ms)
    return {
        "query": payload.query,
        "source": "opac_live_query",
        "count": len(opac_results),
        "results": opac_results,
    }


@app.post("/query/hybrid")
def query_books_hybrid(payload: HybridQueryRequest):
    logger.info(
        "/query/hybrid received | q=%r | llm_suggestions=%s | limit=%s | year_from=%s | year_to=%s | material_type=%r",
        payload.query,
        payload.llm_suggestions,
        payload.limit,
        payload.year_from,
        payload.year_to,
        payload.material_type,
    )
    suggestions = suggest_books_from_llm(payload.query, payload.llm_suggestions)
    pairs = [(item.title, item.author) for item in suggestions]
    logger.info(
        "/query/hybrid llm suggestions parsed | suggestions_count=%s",
        len(pairs),
    )

    started = perf_counter()

    if not pairs:
        logger.warning("/query/hybrid no llm suggestions | fallback=opac_query_text")
        opac_results = []
        try:
            scraper = OpacScraper(logger=logger)
            try:
                candidates = scraper.search_books_live(
                    title=payload.query,
                    author=None,
                    limit=payload.limit,
                    material_type=payload.material_type,
                )
                for book in candidates:
                    if not _passes_filters(
                        {
                            "year": book.year,
                            "material_type": book.material_type,
                        },
                        year_from=payload.year_from,
                        year_to=payload.year_to,
                        material_type=payload.material_type,
                    ):
                        continue

                    opac_results.append(_book_to_result(book))
                    if len(opac_results) >= payload.limit:
                        break
            finally:
                scraper.close()
        except Exception as exc:
            logger.warning("/query/hybrid opac text fallback failed | error=%s", exc)

        return {
            "query": payload.query,
            "source": "opac_live_query_text",
            "llm_suggestions": [item.model_dump() for item in suggestions],
            "count": len(opac_results),
            "results": opac_results,
        }

    # First choice for hybrid: live OPAC lookup using LLM title+author suggestions.
    opac_live_results = []
    try:
        scraper = OpacScraper(logger=logger)
        try:
            seen_ids: set[str] = set()
            max_pairs = min(len(pairs), max(payload.limit * 2, 8))
            for title, author in pairs[:max_pairs]:
                candidates = scraper.search_books_live(
                    title=title,
                    author=author,
                    limit=1,
                    material_type=payload.material_type,
                )
                for book in candidates:
                    if book.id in seen_ids:
                        continue

                    if not _passes_filters(
                        {
                            "year": book.year,
                            "material_type": book.material_type,
                        },
                        year_from=payload.year_from,
                        year_to=payload.year_to,
                        material_type=payload.material_type,
                    ):
                        continue

                    seen_ids.add(book.id)
                    opac_live_results.append(_book_to_result(book))

                    if len(opac_live_results) >= payload.limit:
                        break

                if len(opac_live_results) >= payload.limit:
                    break
        finally:
            scraper.close()
    except Exception as exc:
        logger.warning("/query/hybrid opac live lookup failed | error=%s", exc)

    if opac_live_results:
        elapsed_ms = int((perf_counter() - started) * 1000)
        logger.info(
            "/query/hybrid completed | source=opac_live_title_author | count=%s | elapsed_ms=%s",
            len(opac_live_results),
            elapsed_ms,
        )
        return {
            "query": payload.query,
            "source": "opac_live_title_author",
            "llm_suggestions": [item.model_dump() for item in suggestions],
            "count": len(opac_live_results),
            "results": opac_live_results,
        }

    # Fast fallback: plain OPAC query on original user text.
    fallback_results = []
    try:
        scraper = OpacScraper(logger=logger)
        try:
            candidates = scraper.search_books_live(
                title=payload.query,
                author=None,
                limit=payload.limit,
                material_type=payload.material_type,
            )
            for book in candidates:
                if not _passes_filters(
                    {
                        "year": book.year,
                        "material_type": book.material_type,
                    },
                    year_from=payload.year_from,
                    year_to=payload.year_to,
                    material_type=payload.material_type,
                ):
                    continue
                fallback_results.append(_book_to_result(book))
                if len(fallback_results) >= payload.limit:
                    break
        finally:
            scraper.close()
    except Exception as exc:
        logger.warning("/query/hybrid opac text fallback after no hybrid matches failed | error=%s", exc)

    elapsed_ms = int((perf_counter() - started) * 1000)
    logger.info(
        "/query/hybrid completed | source=opac_live_query_text_after_no_hybrid | count=%s | elapsed_ms=%s",
        len(fallback_results),
        elapsed_ms,
    )
    return {
        "query": payload.query,
        "source": "opac_live_query_text_after_no_hybrid",
        "llm_suggestions": [item.model_dump() for item in suggestions],
        "count": len(fallback_results),
        "results": fallback_results,
    }
