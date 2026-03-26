import "server-only";
import { createAgent, tool } from "langchain";
import { ChatOpenAI } from "@langchain/openai";
import { z } from "zod";
import { checkAvailabilityByTitle, searchBooks } from "@/lib/catalog";

const searchBooksTool = tool(
  async ({ query, genre }) => {
    const books = searchBooks(query, genre.trim() ? genre : undefined);
    return JSON.stringify(books);
  },
  {
    name: "search_books",
    description:
      "Cerca nel catalogo locale in base agli interessi dell'utente e a un genere preferito opzionale.",
    schema: z.object({
      query: z
        .string()
        .describe("Testo libero con interessi utente, temi, tono desiderato o autori preferiti."),
      genre: z
        .string()
        .describe("Genere preferito se indicato esplicitamente dall'utente, altrimenti stringa vuota."),
    }),
  },
);

const checkAvailabilityTool = tool(
  async ({ title }) => {
    const availability = await checkAvailabilityByTitle(title);
    if (!availability) {
      return JSON.stringify({
        title,
        library: "N/A",
        availableCopies: 0,
        shelfCode: "N/A",
        source: "opac",
      });
    }

    return JSON.stringify(availability);
  },
  {
    name: "check_library_availability",
    description: "Verifica se un titolo specifico e disponibile nel catalogo della biblioteca.",
    schema: z.object({
      title: z.string().describe("Titolo esatto del libro da verificare."),
    }),
  },
);

const recommendationSchema = z.object({
  assistantReply: z
    .string()
    .describe("Risposta amichevole in italiano con indicazioni brevi e pratiche."),
  recommendations: z
    .array(
      z.object({
        title: z.string(),
        author: z.string(),
        whyItFits: z.string(),
        availableCopies: z.number(),
        library: z.string(),
        shelfCode: z.string(),
      }),
    )
    .max(3),
});

export const bookAdvisorAgent = createAgent({
  model: new ChatOpenAI({
    model: "gpt-4o-mini",
    apiKey: process.env.OPENAI_API_KEY,
  }),
  tools: [searchBooksTool, checkAvailabilityTool],
  responseFormat: recommendationSchema,
  systemPrompt: `Sei ai-next-book, un assistente che consiglia libri.

Obiettivi:
- Comprendi i gusti dell'utente e fai domande di approfondimento concise quando necessario.
- Suggerisci al massimo 3 libri.
- Verifica sempre la disponibilita chiamando check_library_availability per ogni titolo suggerito.
- Rispondi sempre in italiano.
- Mantieni un tono caldo e pratico.

Se l'input dell'utente e vago, fai una sola domanda di chiarimento in assistantReply e restituisci un array recommendations vuoto.`,
});

export type AgentResponse = z.infer<typeof recommendationSchema>;
