"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useChat } from "@/hooks/useChat";
import { MessageList } from "@/components/MessageList";
import { ChatInput } from "@/components/ChatInput";
import { StatusBar } from "@/components/StatusBar";
import { supabase } from "@/lib/supabase";
import type { User } from "@supabase/supabase-js";
import { getConversations } from "@/lib/api";

interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export default function ChatPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedConv, setSelectedConv] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  const { messages, isLoading, error, send } = useChat({
    conversationId: selectedConv,
    onConversationCreated: (id) => {
      setSelectedConv(id);
      loadConversations();
    },
  });

  const loadConversations = async () => {
    try {
      const data = await getConversations();
      setConversations((data as { conversations: Conversation[] }).conversations ?? []);
    } catch {}
  };

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (!data.session) {
        router.replace("/login");
      } else {
        setUser(data.session.user);
        setLoading(false);
        loadConversations();
      }
    });
  }, [router]);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    router.replace("/login");
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-500">Cargando...</p>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className={`${sidebarOpen ? "w-64" : "w-0"} transition-all duration-200 bg-white border-r overflow-hidden flex flex-col`}>
        <div className="p-4 border-b flex items-center justify-between">
          <h2 className="font-semibold text-gray-800">Conversaciones</h2>
          <button onClick={() => setSidebarOpen(false)} className="text-gray-400 hover:text-gray-600">✕</button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {conversations.map((conv) => (
            <button
              key={conv.id}
              onClick={() => setSelectedConv(conv.id)}
              className={`w-full text-left px-4 py-3 border-b hover:bg-gray-50 ${selectedConv === conv.id ? "bg-blue-50" : ""}`}
            >
              <p className="text-sm font-medium text-gray-800 truncate">{conv.title}</p>
              <p className="text-xs text-gray-400">{new Date(conv.updated_at || conv.created_at).toLocaleDateString("es-AR")}</p>
            </button>
          ))}
          {conversations.length === 0 && (
            <p className="px-4 py-3 text-sm text-gray-400">Sin conversaciones aún</p>
          )}
        </div>
        <div className="p-4 border-t">
          <button onClick={handleLogout} className="text-sm text-red-600 hover:text-red-700">Cerrar sesión</button>
        </div>
      </aside>

      {/* Main chat */}
      <main className="flex-1 flex flex-col">
        <header className="bg-white border-b px-6 py-4 shadow-sm flex items-center gap-3">
          <button onClick={() => setSidebarOpen(true)} className="text-gray-500 hover:text-gray-700">☰</button>
          <div>
            <h1 className="text-xl font-semibold text-gray-800">IAchitecter</h1>
            <p className="text-sm text-gray-500">{user?.email}</p>
          </div>
        </header>

        <div className="flex-1 overflow-hidden flex flex-col max-w-3xl mx-auto w-full px-4 py-4 gap-4">
          <MessageList messages={messages} />
          <StatusBar isLoading={isLoading} />
          {error && (
            <div className="text-red-600 text-sm bg-red-50 rounded px-3 py-2">{error}</div>
          )}
          <ChatInput onSend={send} disabled={isLoading} />
        </div>
      </main>
    </div>
  );
}