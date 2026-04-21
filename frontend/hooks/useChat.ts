import { useState, useCallback } from "react";
import { nanoid } from "nanoid";
import { sendMessage } from "@/lib/api";
import { MessageWithMeta, ChatMessage } from "@/lib/types";

const PROJECT_ID = "demo-project-001";

export function useChat() {
  const [messages, setMessages] = useState<MessageWithMeta[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const send = useCallback(async (text: string) => {
    if (!text.trim() || isLoading) return;
    setError(null);

    const userMsg: MessageWithMeta = {
      id: nanoid(),
      role: "user",
      content: text,
      timestamp: new Date(),
    };
    const loadingMsg: MessageWithMeta = {
      id: nanoid(),
      role: "assistant",
      content: "",
      timestamp: new Date(),
      isLoading: true,
    };

    setMessages((prev) => [...prev, userMsg, loadingMsg]);
    setIsLoading(true);

    const history: ChatMessage[] = [...messages, userMsg].map(
      ({ role, content }) => ({ role, content })
    );

    try {
      const response = await sendMessage({ project_id: PROJECT_ID, messages: history });
      setMessages((prev) =>
        prev.map((m) =>
          m.isLoading
            ? {
                ...m,
                content: response.reply,
                isLoading: false,
                toolCalls: response.tool_calls_executed,
              }
            : m
        )
      );
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Error desconocido";
      setError(msg);
      setMessages((prev) => prev.filter((m) => !m.isLoading));
    } finally {
      setIsLoading(false);
    }
  }, [messages, isLoading]);

  return { messages, isLoading, error, send };
}