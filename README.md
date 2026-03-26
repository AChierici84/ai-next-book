# RAG biblioteca

Servizio Python separato per:

- estrarre libri da OPAC Reggio Emilia anno per anno
- salvare i documenti in ChromaDB
- esporre una FastAPI interrogabile dalla UI web

## Stack

- Playwright per navigare la paginazione JS di OPAC
- BeautifulSoup per parsing HTML
- ChromaDB come vector store persistente
- sentence-transformers per embeddings multilingua
- FastAPI per la query API

## Setup

```powershell
cd rag
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
```

## Ingest iniziale

Esempio: dal 2026 al 2024

```powershell
python ingest_opac.py --start-year 2026 --end-year 2024
```

Esempio rapido limitando le pagine per test:

```powershell
python ingest_opac.py --start-year 2026 --end-year 2026 --max-pages-per-year 3
```

I dati vengono salvati in `rag/data/chroma`.

## Avvio API

```powershell
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

### Query semantica

```http
POST /query
Content-Type: application/json

{
  "query": "romanzo storico ambientato in italia",
  "limit": 5,
  "year_from": 2020,
  "year_to": 2026
}
```

## Integrazione con la UI web

La UI Next.js puo chiamare la FastAPI su `http://localhost:8001/query` e usare i risultati come sorgente RAG per suggerimenti piu accurati.

## Note operative

- La paginazione di OPAC e gestita via JavaScript: per questo l'ingest usa Playwright.
- Il crawler visita la pagina anno, attraversa le pagine risultati e poi arricchisce i record aprendo le schede dettaglio.
- Per ingest molto grandi conviene eseguire per blocchi di anni.
