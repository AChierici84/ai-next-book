# ai-next-book (web)

Chat assistant per aiutare l'utente a scegliere un libro e verificarne la disponibilita in biblioteca.

## Stack

- Next.js (App Router, TypeScript)
- LangChain JS (agent + tool calling)
- OpenAI model via provider `openai:*`

## Flusso MVP

1. Utente scrive preferenze in chat.
2. L'agent usa `search_books` sul catalogo locale mock.
3. L'agent usa `check_library_availability` per i titoli suggeriti.
4. Il tool interroga OPAC Reggio Emilia su `https://opac.provincia.re.it/opac/query/{titolo}?context=catalogo`.
5. Se OPAC non risponde o non e parsabile, usa fallback ai dati mock locali.
6. API restituisce risposta strutturata:
	- `assistantReply`
	- `recommendations[]` con copie disponibili, biblioteca e scaffale.

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
- `src/app/api/chat/route.ts`: endpoint chat che invoca LangChain.
- `src/lib/agent.ts`: definizione agent e tool.
- `src/lib/catalog.ts`: catalogo mock + disponibilita mock.

## Prossimi passi consigliati

- Sostituire `catalog.ts` con DB/Vector Store reale.
- Collegare un'API reale del sistema bibliotecario.
- Aggiungere autenticazione e cronologia utente.
