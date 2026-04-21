"use client";
import { useChat } from "@/hooks/useChat";
import { MessageList } from "@/components/MessageList";
import { ChatInput } from "@/components/ChatInput";
import { StatusBar } from "@/components/StatusBar";

export default function ChatPage() {
  const { messages, isLoading, error, send } = useChat();

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-4 shadow-sm">
        <h1 className="text-xl font-semibold text-gray-800">IAchitecter</h1>
        <p className="text-sm text-gray-500">Presupuestador de obra con IA</p>
      </header>

      <main className="flex-1 overflow-hidden flex flex-col max-w-3xl mx-auto w-full px-4 py-4 gap-4">
        <MessageList messages={messages} />
        <StatusBar isLoading={isLoading} />
        {error && (
          <div className="text-red-600 text-sm bg-red-50 rounded px-3 py-2">
            {error}
          </div>
        )}
        <ChatInput onSend={send} disabled={isLoading} />
      </main>
    </div>
  );
}