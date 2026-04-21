import { MessageWithMeta } from "@/lib/types";

interface MessageBubbleProps {
  message: MessageWithMeta;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={`flex ${isUser ? "justify-end" : "justify-start"}`}
    >
      <div
        className={`max-w-[80%] rounded-lg px-4 py-2 ${
          isUser
            ? "bg-blue-600 text-white"
            : "bg-gray-200 text-gray-800"
        }`}
      >
        {message.isLoading ? (
          <div className="flex gap-1">
            <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
            <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
            <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
          </div>
        ) : (
          <>
            <p className="whitespace-pre-wrap">{message.content}</p>
            {message.toolCalls && message.toolCalls.length > 0 && (
              <div className="mt-2 pt-2 border-t border-gray-400/30 text-xs">
                <span className="font-medium">⚙ </span>
                {message.toolCalls.join(" → ")}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}