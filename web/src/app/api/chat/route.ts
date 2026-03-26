import { NextResponse } from "next/server";
import {
  runBookAdvisor,
  type AgentResponse,
  type ClientMessage,
} from "@/lib/server/bookAdvisorRunner";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

function toAgentMessages(history: ClientMessage[], input: string) {
  const safeHistory = history.slice(-8).map((msg) => ({
    role: msg.role,
    content: msg.content,
  }));

  return [...safeHistory, { role: "user" as const, content: input }];
}

export async function POST(req: Request) {
  try {
    if (!process.env.OPENAI_API_KEY) {
      return NextResponse.json(
        {
          error:
            "OPENAI_API_KEY non configurata. Aggiungila in .env.local per usare la chat.",
        },
        { status: 500 },
      );
    }

    const body = (await req.json()) as {
      input?: string;
      history?: ClientMessage[];
    };

    const input = body.input?.trim();
    if (!input) {
      return NextResponse.json({ error: "Messaggio vuoto." }, { status: 400 });
    }

    const messages = toAgentMessages(body.history ?? [], input);
    const structured: AgentResponse = await runBookAdvisor(messages);

    return NextResponse.json(structured);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Errore sconosciuto";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
