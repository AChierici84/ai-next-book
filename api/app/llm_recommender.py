import json
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from openai import OpenAI

from app.config import settings
from app.models import LlmSuggestion

logger = logging.getLogger(__name__)


def _build_prompt(query: str, n: int) -> str:
    strict_rules = (
            "- NON fare domande all'utente\n"
            "- DIVIETO ASSOLUTO: non chiedere chiarimenti, conferme o permessi\n"
            "- NON chiedere se puoi usare il web\n"
            "- NON inserire il campo request o altri campi extra\n"
            "- Se sei incerto, fornisci comunque titoli noti e plausibili\n"
    )

    return (
        "Sei un esperto bibliotecario. "
        "Rispondi SOLO con JSON valido, senza testo extra, senza markdown, senza backtick. "
        'Formato esatto: {"books":[{"title":"...","author":"..."}]}. '
        "REGOLE IMPORTANTI:\n"
        "- Cita SOLO libri realmente esistenti e pubblicati\n"
        "- NON inventare titoli o autori\n"
        "- Includi classici e libri molto conosciuti se pertinenti\n"
        f"{strict_rules}"
        f"Elenca {n} libri reali che corrispondono a questa richiesta: {query}"
    )


def _build_non_empty_retry_prompt(query: str, n: int) -> str:
    return (
        "Sei un esperto bibliotecario. "
        "Rispondi SOLO con JSON valido, senza testo extra, senza markdown. "
        'Formato esatto: {"books":[{"title":"...","author":"..."}]}. '
        "REGOLE:\n"
        "- NON restituire mai books vuoto\n"
        "- Restituisci almeno 20 libri\n"
        "- Se non sei sicuro della pertinenza perfetta, proponi comunque titoli italiani noti e plausibili per la richiesta\n"
        "- NON fare domande all'utente\n"
        "- DIVIETO ASSOLUTO: non chiedere chiarimenti, conferme o permessi\n"
        "- NON aggiungere testo diverso da books\n"
        f"Fornisci {n} suggerimenti per: {query}"
    )


def _parse_json_payload(raw_text: str) -> dict | list:
    text = raw_text.strip()
    if text.startswith("```"):
        lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    return json.loads(text)


def _extract_items(data: dict | list) -> list[dict]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]

    for key in ("books", "items", "results", "libri", "suggestions"):
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

    return []


def suggest_books_from_llm(query: str, n: int = 20) -> list[LlmSuggestion]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        logger.warning("llm suggestions skipped | reason=missing_openai_api_key")
        return []

    suggestion_count = min(max(n, 1), 8)
    client = OpenAI(api_key=api_key, timeout=settings.llm_timeout_seconds)
    model = os.getenv("LLM_MODEL", "gpt-5-mini")

    prompt = _build_prompt(query=query, n=suggestion_count)
    logger.info(
        "llm suggestions start | model=%s | requested_n=%s | actual_n=%s | timeout_s=%s | query=%r",
        model,
        n,
        suggestion_count,
        settings.llm_timeout_seconds,
        query,
    )

    try:
        resp = client.responses.create(model=model, input=prompt)
        raw_output = (resp.output_text or "").strip()
        logger.info("llm raw output | preview=%r", raw_output[:1200])
        data = _parse_json_payload(raw_output)
        items = _extract_items(data)

        if not items:
            logger.warning("llm returned empty books on first attempt | retrying with non-empty prompt")
            retry_prompt = _build_non_empty_retry_prompt(query=query, n=suggestion_count)
            retry_resp = client.responses.create(model=model, input=retry_prompt)
            retry_raw_output = (retry_resp.output_text or "").strip()
            logger.info("llm raw output retry | preview=%r", retry_raw_output[:1200])
            retry_data = _parse_json_payload(retry_raw_output)
            retry_items = _extract_items(retry_data)
            if retry_items:
                items = retry_items

        out: list[LlmSuggestion] = []
        for it in items[:suggestion_count]:
            title = str(it.get("title") or it.get("titolo") or "").strip()
            author = str(it.get("author") or it.get("autore") or "").strip() or None
            if title:
                out.append(LlmSuggestion(title=title, author=author, isbn=None))
        logger.info(
            "llm suggestions completed | parsed=%s | preview=%r",
            len(out),
            [
                {"title": item.title, "author": item.author}
                for item in out[:5]
            ],
        )
        return out
    except Exception as exc:
        logger.exception("llm suggestions failed | error=%s", exc)
        return []