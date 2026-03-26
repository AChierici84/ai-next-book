from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path

from app.chroma_store import ChromaBookStore
from app.models import IngestSummary
from app.opac_scraper import OpacScraper


def parse_args() -> argparse.Namespace:
    current_year = datetime.now().year
    parser = argparse.ArgumentParser(description="Ingest OPAC books into ChromaDB year by year.")
    parser.add_argument("--start-year", type=int, default=current_year)
    parser.add_argument("--end-year", type=int, default=2000)
    parser.add_argument("--max-pages-per-year", type=int, default=None)
    return parser.parse_args()


def configure_logging() -> tuple[logging.Logger, Path]:
    logs_dir = Path(__file__).resolve().parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = logs_dir / f"ingest-opac-{timestamp}.log"

    logger = logging.getLogger("ingest_opac")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger, log_path


def main() -> None:
    args = parse_args()
    logger, log_path = configure_logging()

    if args.end_year > args.start_year:
        raise SystemExit("end-year deve essere minore o uguale a start-year")

    store = ChromaBookStore()
    years_processed = 0
    documents_upserted = 0

    logger.info(
        "Inizio ingest OPAC | start_year=%s end_year=%s max_pages_per_year=%s log_file=%s",
        args.start_year,
        args.end_year,
        args.max_pages_per_year,
        log_path,
    )

    scraper = OpacScraper(logger=logger)

    try:
        for year in range(args.start_year, args.end_year - 1, -1):
            logger.info("Avvio elaborazione anno %s", year)
            books = scraper.crawl_year(year, max_pages=args.max_pages_per_year)
            saved_count = store.upsert_books(books)
            documents_upserted += saved_count
            years_processed += 1
            logger.info("Anno %s completato | libri estratti=%s libri salvati=%s", year, len(books), saved_count)
    except Exception:
        logger.exception("Ingest OPAC fallita")
        raise
    finally:
        scraper.close()
        logger.info("Scraper HTTP chiuso")

    summary = IngestSummary(years_processed=years_processed, documents_upserted=documents_upserted)
    logger.info("Riepilogo ingest: %s", summary.model_dump_json())
    print(summary.model_dump_json(indent=2))
    print(f"Log scritto in: {log_path}")


if __name__ == "__main__":
    main()
