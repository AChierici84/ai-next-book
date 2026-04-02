import { NextRequest, NextResponse } from "next/server";

const API_BASE =
  process.env.OPAC_API_BASE_URL ??
  process.env.RAG_API_BASE_URL ??
  "http://localhost:8001";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000);

    try {
      const upstream = await fetch(`${API_BASE}/export/pdf`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: body.query,
          books: body.books,
        }),
        cache: "no-store",
        signal: controller.signal,
      });

      if (!upstream.ok) {
        let errorMessage = "Errore durante l'export PDF.";

        try {
          const data = (await upstream.json()) as { detail?: string; error?: string };
          errorMessage = data.detail ?? data.error ?? errorMessage;
        } catch {
          const text = await upstream.text();
          if (text) {
            errorMessage = text;
          }
        }

        return NextResponse.json({ error: errorMessage }, { status: upstream.status });
      }

      const pdfBuffer = await upstream.arrayBuffer();
      const contentDisposition =
        upstream.headers.get("content-disposition") ??
        'attachment; filename="libri_suggeriti.pdf"';

      return new NextResponse(pdfBuffer, {
        status: 200,
        headers: {
          "Content-Type": "application/pdf",
          "Content-Disposition": contentDisposition,
        },
      });
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") {
        return NextResponse.json(
          { error: "Export PDF troppo lento. Riprova tra qualche secondo." },
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