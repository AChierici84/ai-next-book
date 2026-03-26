from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from math import ceil
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup, Tag
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright
from tenacity import retry, stop_after_attempt, wait_fixed

from app.config import settings
from app.models import BookDocument


RESULTS_PER_PAGE = 10


@dataclass
class YearPageSnapshot:
    books: list[BookDocument]
    total_results: int
    total_pages: int


class OpacScraper:
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._http = httpx.Client(
            timeout=settings.request_timeout_seconds,
            headers={"User-Agent": settings.user_agent},
            follow_redirects=True,
        )
        self._logger = logger

    def close(self) -> None:
        self._http.close()

    def build_year_url(self, year: int) -> str:
        # KF_KITH:"testo a stampa (moderno)" restricts search to physical modern printed books.
        return (
            f"{settings.opac_base_url}/opac/query/"
            f"ANNOFASC:{year}%20KF_KITH:%22testo%20a%20stampa%20(moderno)%22"
            "?context=catalogo&sort=Anno"
        )

    def crawl_year(self, year: int, max_pages: int | None = None) -> list[BookDocument]:
        year_url = self.build_year_url(year)
        if self._logger:
            self._logger.info("Anno %s | apertura URL %s", year, year_url)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=settings.headless_browser)
            page = browser.new_page(user_agent=settings.user_agent)
            page.goto(year_url, wait_until="domcontentloaded")
            page.wait_for_selector("li[id^='listadocumenti_']", timeout=15000)

            first_snapshot = self._parse_results_html(page.content(), year)
            total_pages = first_snapshot.total_pages
            if max_pages is not None:
                total_pages = min(total_pages, max_pages)

            if self._logger:
                self._logger.info(
                    "Anno %s | pagina 1/%s letta | risultati stimati=%s",
                    year,
                    total_pages,
                    first_snapshot.total_results,
                )

            seen: dict[str, BookDocument] = {book.id: book for book in first_snapshot.books}
            current_page = 1

            while current_page < total_pages:
                next_link = page.locator("footer.listarisultati-piede a[title='vai alla pagina successiva']")
                if next_link.count() == 0:
                    break
                next_link.first.click()
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except PlaywrightTimeoutError:
                    page.wait_for_timeout(1000)
                page.wait_for_selector("li[id^='listadocumenti_']", timeout=15000)
                current_page += 1
                snapshot = self._parse_results_html(page.content(), year)
                if self._logger:
                    self._logger.info(
                        "Anno %s | pagina %s/%s letta | record unici=%s",
                        year,
                        current_page,
                        total_pages,
                        len(seen),
                    )
                for book in snapshot.books:
                    seen[book.id] = book

            browser.close()

        if self._logger:
            self._logger.info("Anno %s | inizio arricchimento dettagli OPAC | record=%s", year, len(seen))

        enriched: list[BookDocument] = []
        total_books = len(seen)
        for index, book in enumerate(seen.values(), start=1):
            enriched.append(self._enrich_book(book))
            if self._logger and (index == total_books or index == 1 or index % 10 == 0):
                self._logger.info(
                    "Anno %s | arricchimento %s/%s completato",
                    year,
                    index,
                    total_books,
                )

        return enriched

    def _parse_results_html(self, html: str, year: int) -> YearPageSnapshot:
        soup = BeautifulSoup(html, "lxml")
        result_items = soup.select("li[id^='listadocumenti_']")
        books: list[BookDocument] = []
        for item in result_items:
            book = self._parse_result_item(item, year)
            if book:
                books.append(book)

        stats_text = soup.select_one("footer.listarisultati-piede li.statistica")
        total_results = 0
        total_pages = 1
        if stats_text:
            match = re.search(r"di\s+([\d\.]+)", stats_text.get_text(" ", strip=True))
            if match:
                total_results = int(match.group(1).replace(".", ""))
                total_pages = max(1, ceil(total_results / RESULTS_PER_PAGE))

        return YearPageSnapshot(books=books, total_results=total_results, total_pages=total_pages)

    def _parse_result_item(self, item: Tag, year: int) -> BookDocument | None:
        title_link = item.select_one("h3 a[href*='/opac/resource/']")
        if not title_link or not title_link.get("href"):
            return None

        source_url = urljoin(settings.opac_base_url, str(title_link["href"]))
        resource_id = source_url.rstrip("/").split("/")[-1]
        title = self._clean_text(title_link.get_text(" ", strip=True))

        text_lines = [self._clean_text(line) for line in item.get_text("\n", strip=True).splitlines()]
        text_lines = [line for line in text_lines if line and line not in {title, "Richiedi", "Richiedi in consultazione"}]

        available_copies = self._extract_number(item.get_text(" ", strip=True), "Disponibili")
        total_copies = self._extract_number(item.get_text(" ", strip=True), "Copie per prestito")
        author = None
        material_type = None
        parsed_year = year

        for line in text_lines[:4]:
            if re.fullmatch(r"\d{4}", line):
                parsed_year = int(line)
                continue
            if any(token in line.lower() for token in ["romanzo", "disc", "audiolibro", "fumetti", "testo", "dvd", "ebook"]):
                material_type = line
                year_match = re.search(r"(19|20)\d{2}", line)
                if year_match:
                    parsed_year = int(year_match.group(0))
                continue
            if not author:
                author = line

        return BookDocument(
            id=resource_id,
            title=title,
            author=author,
            year=parsed_year,
            material_type=material_type,
            source_url=source_url,
            query_year=year,
            available_copies=available_copies,
            total_copies=total_copies,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    def _enrich_book(self, book: BookDocument) -> BookDocument:
        response = self._http.get(book.source_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")

        abstract = self._extract_abstract(soup)
        libraries = self._extract_libraries(soup)
        author = book.author or self._extract_author(soup)
        material_type = book.material_type or self._extract_material_type(soup)
        year = book.year or self._extract_year(soup)

        return book.model_copy(
            update={
                "summary": abstract,
                "libraries": libraries,
                "author": author,
                "material_type": material_type,
                "year": year,
            }
        )

    def _extract_abstract(self, soup: BeautifulSoup) -> str | None:
        abstract_header = soup.find(["summary", "h3"], string=re.compile("Abstract", re.I))
        if abstract_header:
            container = abstract_header.find_parent(["details", "div", "section"])
            if container:
                text = self._clean_text(container.get_text(" ", strip=True))
                return text[:4000] if text else None
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            return self._clean_text(str(meta_desc["content"]))[:4000]
        return None

    def _extract_libraries(self, soup: BeautifulSoup) -> list[str]:
        section = soup.select_one("section#biblioteche")
        if not section:
            return []
        libraries = []
        for link in section.select("a"):
            text = self._clean_text(link.get_text(" ", strip=True))
            if text:
                libraries.append(text)
        return libraries[:10]

    def _extract_author(self, soup: BeautifulSoup) -> str | None:
        title_text = soup.title.get_text(" ", strip=True) if soup.title else ""
        if "|" in title_text:
            title_text = title_text.split("|")[0]
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            content = self._clean_text(str(meta_desc["content"]))
            segments = [segment.strip() for segment in content.split("/")]
            if len(segments) > 1:
                return segments[1][:250]
        return None

    def _extract_material_type(self, soup: BeautifulSoup) -> str | None:
        tag = soup.select_one("span[class*='meta-tipodocumento'], span[class*='tdoc-']")
        return self._clean_text(tag.get_text(" ", strip=True)) if tag else None

    def _extract_year(self, soup: BeautifulSoup) -> int | None:
        tag = soup.select_one("span.meta-annopubblicazione")
        if not tag:
            return None
        match = re.search(r"(19|20)\d{2}", tag.get_text(" ", strip=True))
        return int(match.group(0)) if match else None

    def _extract_number(self, text: str, label: str) -> int | None:
        match = re.search(rf"{label}:\s*(\d+)", text, re.I)
        return int(match.group(1)) if match else None

    def _clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()
