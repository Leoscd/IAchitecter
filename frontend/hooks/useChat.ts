import { useState, useCallback, useEffect } from "react";
import { nanoid } from "nanoid";
import { sendMessage, createConversation, addMessage, getConversation } from "@/lib/api";
import { MessageWithMeta, ChatMessage } from "@/lib/types";

const PROJECT_ID = "demo-project-001";

interface UseChatOptions {
  conversationId?: string | null;
  onConversationCreated?: (id: string) => void;
}

export function useChat({ conversationId, onConversationCreated }: UseChatOptions = {}) {
  const [messages, setMessages] = useState<MessageWithMeta[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentConvId, setCurrentConvId] = useState<string | null>(conversationId ?? null);

  // Load conversation messages on mount
  useEffect(() => {
    if (conversationId) {
      getConversation(conversationId)
        .then((data: { messages: Array<{ role: string; content: string; created_at: string }> }) => {
          if (data.messages && Array.isArray(data.messages)) {
            const loaded: MessageWithMeta[] = data.messages.map((m) => ({
              id: nanoid(),
              role: m.role as "user" | "assistant",
              content: m.content,
              timestamp: new Date(m.created_at),
            }));
            setMessages(loaded);
          }
        })
        .catch(() => {});
    }
  }, [conversationId]);

  const send = useCallback(
    async (text: string) => {
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

      const history: ChatMessage[] = [...messages, userMsg].map(({ role, content }) => ({ role, content }));

      try {
        // Create conversation if none exists
        let convId = currentConvId;
        if (!convId) {
          const newConv = await createConversation(`Proyecto ${PROJECT_ID}`);
          convId = newConv.id ?? newConv.conversation?.id ?? null;
          setCurrentConvId(convId);
          if (convId) onConversationCreated?.(convId);
        }

        if (!convId) throw new Error("No se pudo crear conversación");

        // Save user message
        await addMessage(convId, "user", text);

        const response = await sendMessage({ project_id: PROJECT_ID, messages: history });

        setMessages((prev) =>
          prev.map((m) =>
            m.isLoading
              ? { ...m, content: response.reply, isLoading: false, toolCalls: response.tool_calls_executed }
              : m
          )
        );

        // Save assistant message
        await addMessage(convId, "assistant", response.reply);
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Error desconocido";
        setError(msg);
        setMessages((prev) => prev.filter((m) => !m.isLoading));
      } finally {
        setIsLoading(false);
      }
    },
    [messages, isLoading, currentConvId, onConversationCreated]
  );

  return { messages, isLoading, error, send };
}