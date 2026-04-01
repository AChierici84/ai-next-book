# OPAC live search

Servizio Python FastAPI per cercare libri direttamente su OPAC Reggio Emilia in tempo reale.

## Stack

- FastAPI per gli endpoint API
- httpx per richieste HTTP verso OPAC
- BeautifulSoup per parsing HTML delle pagine OPAC
- OpenAI (opzionale) per suggerimenti titolo/autore in query ibrida

## Setup

```powershell
cd api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install openai python-dotenv
python -m playwright install chromium
```

## Configurazione (opzionale per /query/hybrid)

Crea il file `api/app/.env`:

```env
OPENAI_API_KEY=YOUR_API_KEY
LLM_MODEL=gpt-5-mini
```

Se `OPENAI_API_KEY` non e impostata, `/query/hybrid` usa il fallback di ricerca OPAC sul testo query.

## Avvio API

```powershell
cd api
uvicorn app.main:app --reload --port 8001
```

## Endpoint

### Health

```http
GET /health
```

### Statistiche

```http
GET /stats
```

In modalita OPAC-only ritorna `documents: 0`.

### Lookup diretto record OPAC

```http
POST /opac/lookup
Content-Type: application/json

{
  "resource_id": "RE201256228"
}
```

oppure

```http
POST /opac/lookup
Content-Type: application/json

{
  "source_url": "https://opac.provincia.re.it/opac/resource/la-ragazza-nella-nebbia-romanzo/RE201256228"
}
```

### Query OPAC live

```http
POST /query
Content-Type: application/json

{
  "query": "giallo italiano ambientato in montagna",
  "limit": 8,
  "year_from": null,
  "year_to": null,
  "material_type": "testo a stampa (moderno)"
}
```

### Query ibrida OPAC live (LLM titolo/autore -> OPAC)

```http
POST /query/hybrid
Content-Type: application/json

{
  "query": "consigliami gialli italiani in montagna",
  "limit": 8,
  "llm_suggestions": 20,
  "year_from": null,
  "year_to": null,
  "material_type": "testo a stampa (moderno)"
}
```

## Integrazione UI

La route Next.js `POST /api/search` inoltra a FastAPI `POST /query/hybrid`.
I risultati mostrati in UI provengono da OPAC live.
