import { NextRequest, NextResponse } from "next/server";

const API_BASE =
  process.env.OPAC_API_BASE_URL ??
  process.env.RAG_API_BASE_URL ??
  "http://localhost:8001";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 25000);

    try {
      const upstream = await fetch(`${API_BASE}/query/hybrid`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: body.query,
          limit: body.limit ?? 8,
          llm_suggestions: body.llm_suggestions ?? 8,
          year_from: body.yearFrom ?? null,
          year_to: body.yearTo ?? null,
          material_type: body.materialType ?? null,
        }),
        cache: "no-store",
        signal: controller.signal,
      });

      const data = await upstream.json();
      if (!upstream.ok) {
        return NextResponse.json({ error: data?.detail ?? "Errore upstream" }, { status: upstream.status });
      }

      return NextResponse.json(data);
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") {
        return NextResponse.json(
          { error: "Ricerca troppo lenta verso OPAC/LLM. Riprova o usa una query piu specifica." },
          { status: 504 },
        );
      }

      throw error;
    } finally {
      clearTimeout(timeout);
    }
  } catch {
    return NextResponse.json({ error: "Richiesta non valida" }, { status: 400 });
  }
}
