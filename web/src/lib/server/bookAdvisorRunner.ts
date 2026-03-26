import "server-only";

export type ClientMessage = {
  role: "user" | "assistant";
  content: string;
};

export type AgentResponse = {
  assistantReply: string;
  recommendations: Array<{
    title: string;
    author: string;
    whyItFits: string;
    availableCopies: number;
    library: string;
    shelfCode: string;
  }>;
};

export async function runBookAdvisor(messages: ClientMessage[]): Promise<AgentResponse> {
  const { bookAdvisorAgent } = await import("@/lib/agent");
  const result = await bookAdvisorAgent.invoke({ messages });
  const structured = result.structuredResponse as AgentResponse | undefined;

  if (!structured) {
    throw new Error("Nessuna risposta strutturata dal modello.");
  }

  return structured;
}
