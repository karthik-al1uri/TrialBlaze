"use client";

import { useState } from "react";
import { Send } from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function ChatPanel() {
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: "Hi! I'm TrailBlaze AI. Ask me about Colorado trails!" },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSend = async () => {
    const query = input.trim();
    if (!query || isLoading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: query }]);
    setIsLoading(true);

    try {
      const res = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });
      const data = await res.json();
      setMessages((prev) => [...prev, { role: "assistant", content: data.answer }]);
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", content: "Error connecting to server." }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white">
      <div className="px-4 py-3 bg-emerald-700">
        <h1 className="text-lg font-bold text-white">TrailBlaze AI</h1>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[80%] rounded-xl px-3 py-2 text-sm ${
              msg.role === "user" ? "bg-emerald-700 text-white" : "bg-gray-100 text-gray-800"
            }`}>
              {msg.content}
            </div>
          </div>
        ))}
        {isLoading && <p className="text-sm text-gray-400">Thinking...</p>}
      </div>

      <div className="p-3 border-t flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Ask about Colorado trails..."
          className="flex-1 px-3 py-2 rounded-lg border text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
          disabled={isLoading}
        />
        <button
          onClick={handleSend}
          disabled={isLoading || !input.trim()}
          className="p-2 rounded-lg bg-emerald-700 text-white disabled:opacity-40"
        >
          <Send className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}
