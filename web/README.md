# ai-next-book (web)

Interfaccia web per cercare libri sul catalogo OPAC Reggio Emilia e verificare disponibilita in tempo reale.

## Stack

- Next.js (App Router, TypeScript)
- LangChain JS (agent + tool calling)
- OpenAI model via provider `openai:*`
- FastAPI backend OPAC live su `http://localhost:8001`

## Flusso MVP

1. La pagina principale invia la richiesta a `POST /api/search`.
2. L'API Next inoltra al backend FastAPI `POST /query/hybrid`.
3. Il backend cerca direttamente su OPAC (titolo/autore suggeriti da LLM oppure query testuale).
4. La UI mostra risultati live con disponibilita e link alla scheda OPAC.

## Setup

1. Installa dipendenze:

```bash
npm install
```

2. Crea il file ambiente:

```bash
cp .env.example .env.local
```

3. Inserisci la chiave OpenAI in `.env.local`:

```bash
OPENAI_API_KEY=your_openai_api_key_here
```

4. Avvia in sviluppo:

```bash
npm run dev
```

Poi apri http://localhost:3000

## File principali

- `src/app/page.tsx`: UI chat + pannello suggerimenti.
- `src/app/api/search/route.ts`: proxy verso FastAPI backend OPAC.
- `src/app/api/chat/route.ts`: endpoint chat che invoca LangChain.
- `src/lib/agent.ts`: definizione agent e tool.
- `src/lib/catalog.ts`: tool di disponibilita OPAC (+ fallback mock per chat).

## Prossimi passi consigliati

- Unificare il flusso chat con la stessa pipeline OPAC live usata nella ricerca.
- Ridurre i fallback mock in produzione.
- Aggiungere telemetria su tempi risposta OPAC e zero-result rate.
