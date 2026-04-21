import { ChatRequest, ChatResponse } from "./types";
import { supabase } from "./supabase";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function getAuthHeaders(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

export async function sendMessage(req: ChatRequest): Promise<ChatResponse> {
  const authHeaders = await getAuthHeaders();
  const res = await fetch(`${BASE_URL}/api/v1/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
    },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Error del servidor");
  }
  return res.json();
}

// History API
export async function getConversations() {
  const authHeaders = await getAuthHeaders();
  const res = await fetch(`${BASE_URL}/api/v1/history`, {
    headers: { ...authHeaders },
  });
  if (!res.ok) throw new Error("Error cargando historial");
  return res.json();
}

export async function getConversation(id: string) {
  const authHeaders = await getAuthHeaders();
  const res = await fetch(`${BASE_URL}/api/v1/history/${id}`, {
    headers: { ...authHeaders },
  });
  if (!res.ok) throw new Error("Error cargando conversación");
  return res.json();
}

export async function createConversation(title: string) {
  const authHeaders = await getAuthHeaders();
  const res = await fetch(`${BASE_URL}/api/v1/history`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
    },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error("Error creando conversación");
  return res.json();
}

export async function addMessage(conversationId: string, role: "user" | "assistant", content: string) {
  const authHeaders = await getAuthHeaders();
  const res = await fetch(`${BASE_URL}/api/v1/history/${conversationId}/messages`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
    },
    body: JSON.stringify({ role, content }),
  });
  if (!res.ok) throw new Error("Error guardando mensaje");
  return res.json();
}