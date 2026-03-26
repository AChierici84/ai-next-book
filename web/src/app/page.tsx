"use client";

import Image from "next/image";
import { FormEvent, useState } from "react";

type SearchResult = {
  id: string;
  title: string;
  author?: string | null;
  year?: number | null;
  material_type?: string | null;
  summary?: string | null;
  libraries: string[];
  available_copies?: number | null;
  total_copies?: number | null;
  source_url: string;
  score: number;
};

type SearchResponse = {
  query: string;
  count: number;
  results: SearchResult[];
};

export default function Home() {
  const [input, setInput] = useState("");
  const [materialType, setMaterialType] = useState("testo a stampa (moderno)");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchedQuery, setSearchedQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    setLoading(true);
    setError(null);
    setSearchedQuery(trimmed);

    try {
      const response = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: trimmed,
          limit: 8,
          materialType: materialType || null,
        }),
      });

      const data = (await response.json()) as SearchResponse | { error: string };
      if (!response.ok || "error" in data) {
        const errorText = "error" in data ? data.error : "Errore durante la richiesta.";
        setError(errorText);
        setResults([]);
        return;
      }

      setResults(data.results);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-gray-50 text-gray-900">
      <header className="border-b border-gray-200 bg-white shadow-sm">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-8">
          <div className="flex items-center gap-3">
            <Image
              src="/logo-re2-polo.png"
              alt="ai-next-book logo"
              width={40}
              height={40}
              className="rounded"
              style={{ height: "auto" }}
            />
            <div className="flex flex-col gap-1">
              <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: "#EA730B" }}>Sistema Bibliotecario Reggiano</p>
              <h1 className="text-xl font-bold text-gray-900">Assistente Bibliotecario Virtuale</h1>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-4 py-8 sm:px-8">
        <div className="rounded-lg bg-white p-6 shadow-sm ring-1 ring-gray-200">
          <p className="text-sm text-gray-700">
            Ricerca semantica sui libri del <a href="https://opac.provincia.re.it/" className="font-semibold hover:underline" style={{ color: "#EA730B" }}>Sistema Bibliotecario Reggiano</a>, alimentata dalla FastAPI RAG e dal catalogo indicizzato in ChromaDB.
          </p>
        </div>

        <section className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
            <div className="border-b border-gray-200 bg-gray-50 px-6 py-4">
              <h2 className="font-semibold text-gray-900">Ricerca RAG</h2>
              <p className="mt-1 text-sm text-gray-600">
                Cerca per temi, atmosfera, autore o tipo di libro. La query verra inviata alla FastAPI locale.
              </p>
            </div>

            <div className="space-y-4 bg-gray-50 p-4">
              <div className="rounded-lg border border-dashed border-gray-300 bg-white p-4 text-sm text-gray-600">
                <p className="font-semibold text-gray-900">Suggerimenti query</p>
                <p className="mt-2">"giallo italiano ambientato in montagna"</p>
                <p>"fantascienza politica con worldbuilding forte"</p>
                <p>"saggio breve su tecnologia e societa"</p>
              </div>

              <div className="rounded-lg bg-white p-4 ring-1 ring-gray-200">
                <p className="text-sm text-gray-600">Endpoint usato</p>
                <p className="mt-1 font-mono text-xs text-gray-800">POST /api/search -&gt; FastAPI /query</p>
              </div>

              {searchedQuery ? (
                <div className="rounded-lg bg-white p-4 ring-1 ring-gray-200">
                  <p className="text-sm text-gray-600">Ultima ricerca</p>
                  <p className="mt-2 inline-block rounded-2xl px-3 py-1 text-sm text-white" style={{ backgroundColor: "#EA730B" }}>
                    {searchedQuery}
                  </p>
                </div>
              ) : null}

              {error ? (
                <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                  {error}
                </div>
              ) : null}
            </div>

            <form onSubmit={onSubmit} className="border-t border-gray-200 bg-gray-50 p-4">
              <div className="mb-3">
                <label htmlFor="material-type" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-600">
                  Tipologia materiale
                </label>
                <select
                  id="material-type"
                  value={materialType}
                  onChange={(event) => setMaterialType(event.target.value)}
                  className="w-full rounded bg-white px-3 py-2 text-sm outline-none"
                  style={{ border: "1px solid #EA730B" }}
                >
                  <option value="testo a stampa (moderno)">Solo libri (testo a stampa moderno)</option>
                  <option value="">Tutte le tipologie</option>
                  <option value="audiolibro">Audiolibri</option>
                  <option value="ebook">Ebook</option>
                  <option value="dvd">DVD</option>
                </select>
              </div>
              <div className="flex gap-2">
                <input
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  placeholder="Es: Mi piace la fantascienza profonda ma non troppo lunga"
                  className="flex-1 rounded bg-white px-3 py-2 text-sm outline-none"
                  style={{
                    border: "1px solid #EA730B",
                    boxShadow: "0 0 0 3px rgba(234, 115, 11, 0.1)",
                  }}
                  onFocus={(e) => {
                    e.target.style.boxShadow = "0 0 0 3px rgba(234, 115, 11, 0.2)";
                  }}
                  onBlur={(e) => {
                    e.target.style.boxShadow = "0 0 0 3px rgba(234, 115, 11, 0.1)";
                  }}
                />
                <button
                  type="submit"
                  disabled={loading}
                  className="rounded px-4 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50"
                  style={{ backgroundColor: "#EA730B" }}
                >
                  {loading ? "Cerco..." : "Cerca"}
                </button>
              </div>
            </form>
          </div>

          <aside className="rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
            <div className="border-b border-gray-200 bg-gray-50 px-4 py-3">
              <h3 className="text-sm font-semibold text-gray-900">Risultati biblioteca</h3>
            </div>
            <div className="space-y-0">
              {results.length === 0 ? (
                <p className="p-4 text-sm text-gray-600">
                  Nessun risultato ancora. Esegui una ricerca per interrogare la RAG della biblioteca.
                </p>
              ) : (
                results.map((book) => (
                  <article key={book.id} className="border-b border-gray-100 p-4 last:border-b-0">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <h3 className="font-semibold text-gray-900">{book.title}</h3>
                        <p className="mt-1 text-sm text-gray-600">
                          {book.author || "Autore non disponibile"}
                          {book.year ? ` - ${book.year}` : ""}
                        </p>
                      </div>
                      <span className="rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-600">
                        score {book.score.toFixed(3)}
                      </span>
                    </div>

                    {book.material_type ? (
                      <p className="mt-2 text-xs uppercase tracking-wide text-gray-500">{book.material_type}</p>
                    ) : null}

                    {book.summary ? <p className="mt-3 text-sm text-gray-800">{book.summary}</p> : null}

                    <div className="mt-3 space-y-1">
                      <p className="text-xs font-semibold text-blue-600">
                        {book.available_copies && book.available_copies > 0
                          ? `Disponibile: ${book.available_copies} copie su ${book.total_copies ?? "?"}`
                          : "Attualmente non disponibile"}
                      </p>
                      {book.libraries.length > 0 ? <p className="text-xs text-gray-600">{book.libraries.join("; ")}</p> : null}
                      <a
                        href={book.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex text-xs font-semibold hover:underline"
                        style={{ color: "#EA730B" }}
                      >
                        Apri scheda OPAC
                      </a>
                    </div>
                  </article>
                ))
              )}
            </div>
          </aside>
        </section>
      </main>

      <footer className="border-t border-gray-200 bg-gray-50 px-4 py-8 text-center text-xs text-gray-600 sm:px-8">
        <p>
          Catalogo in collaborazione con{" "}
          <a href="https://opac.provincia.re.it/" className="font-semibold hover:underline" style={{ color: "#EA730B" }}>
            OPAC Reggio Emilia
          </a>
        </p>
      </footer>
    </div>
  );
}
