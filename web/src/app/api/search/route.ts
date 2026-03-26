import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const DEFAULT_RAG_API_URL = "http://127.0.0.1:8001";

export async function POST(req: Request) {
  try {
    const body = (await req.json()) as {
      query?: string;
      limit?: number;
      yearFrom?: number | null;
      yearTo?: number | null;
      materialType?: string | null;
    };

    const query = body.query?.trim();
    if (!query) {
      return NextResponse.json({ error: "Query vuota." }, { status: 400 });
    }

    const ragApiUrl = process.env.RAG_API_URL?.trim() || DEFAULT_RAG_API_URL;
    const upstream = await fetch(`${ragApiUrl}/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      cache: "no-store",
      body: JSON.stringify({
        query,
        limit: body.limit ?? 8,
        year_from: body.yearFrom ?? null,
        year_to: body.yearTo ?? null,
        material_type: body.materialType?.trim() ? body.materialType.trim() : null,
      }),
    });

    const data = await upstream.json();
    if (!upstream.ok) {
      const error = typeof data?.detail === "string" ? data.detail : "Errore dalla FastAPI RAG.";
      return NextResponse.json({ error }, { status: upstream.status });
    }

    return NextResponse.json(data);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Errore sconosciuto";
    return NextResponse.json(
      { error: `Impossibile contattare la FastAPI RAG: ${message}` },
      { status: 500 },
    );
  }
}
