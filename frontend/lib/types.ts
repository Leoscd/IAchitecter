export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  project_id: string;
  messages: ChatMessage[];
}

export interface ChatResponse {
  reply: string;
  tool_calls_executed: string[];
  rounds: number;
}

export type MessageWithMeta = ChatMessage & {
  id: string;           // nanoid para key React
  timestamp: Date;
  toolCalls?: string[]; // funciones ejecutadas en ese turno
  isLoading?: boolean;
};