"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Mountain, Bot, User, Calendar, Mic, MicOff, Globe } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { sendChat, generateItinerary, type ChatResponse, type TrailReference } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
  trails?: TrailReference[];
  weatherContext?: string;
  route?: string;
}

interface ChatPanelProps {
  onTrailsReferenced?: (trails: TrailReference[], weather?: string) => void;
  sessionId?: string;
  onSessionCreated?: (id: string) => void;
}

export default function ChatPanel({
  onTrailsReferenced,
  sessionId,
  onSessionCreated,
}: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Hey there! 🏔️ I'm TrailBlaze AI, your Colorado trail guide. Ask me about trails, difficulty levels, weather, or anything outdoor-related!",
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [itineraryLoading, setItineraryLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [chatLang, setChatLang] = useState<"en" | "es">("en");
  const recognitionRef = useRef<any>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    const query = input.trim();
    if (!query || isLoading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: query }]);
    setIsLoading(true);

    try {
      const res: ChatResponse = await sendChat(query, sessionId, chatLang);

      if (res.session_id && onSessionCreated) {
        onSessionCreated(res.session_id);
      }

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.answer,
          trails: res.trails_referenced,
          weatherContext: res.weather_context || undefined,
          route: res.route,
        },
      ]);

      if (onTrailsReferenced) {
        onTrailsReferenced(
          res.trails_referenced || [],
          res.weather_context || undefined
        );
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "Sorry, I had trouble connecting. Make sure the backend server is running on port 8000.",
        },
      ]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-200 bg-gradient-to-r from-emerald-800 to-emerald-700">
        <Mountain className="w-6 h-6 text-amber-400" />
        <div className="flex-1">
          <h1 className="text-lg font-bold text-white leading-tight">
            TrailBlaze AI
          </h1>
          <p className="text-xs text-emerald-200">Colorado Trail Guide</p>
        </div>
        <button
          onClick={() => setChatLang((prev) => (prev === "en" ? "es" : "en"))}
          className="flex items-center gap-1 px-2 py-1 rounded-full bg-white/15 hover:bg-white/25 text-white text-[11px] font-medium transition-colors"
          title="Toggle language"
        >
          <Globe className="w-3.5 h-3.5" />
          {chatLang === "en" ? "EN" : "ES"}
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 chat-messages">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex gap-2 ${
              msg.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            {msg.role === "assistant" && (
              <div className="w-7 h-7 rounded-full bg-emerald-100 flex items-center justify-center shrink-0 mt-0.5">
                <Bot className="w-3.5 h-3.5 text-emerald-700" />
              </div>
            )}
            <div
              className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-[13px] leading-relaxed ${
                msg.role === "user"
                  ? "bg-emerald-700 text-white rounded-br-md"
                  : "bg-gray-100 text-gray-800 rounded-bl-md"
              }`}
            >
              <div className="prose-chat">
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              </div>
            </div>
            {msg.role === "user" && (
              <div className="w-7 h-7 rounded-full bg-emerald-700 flex items-center justify-center shrink-0 mt-0.5">
                <User className="w-3.5 h-3.5 text-white" />
              </div>
            )}
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-2 justify-start">
            <div className="w-7 h-7 rounded-full bg-emerald-100 flex items-center justify-center shrink-0">
              <Bot className="w-3.5 h-3.5 text-emerald-700" />
            </div>
            <div className="bg-gray-100 rounded-2xl rounded-bl-md px-4 py-3 flex gap-1">
              <span className="typing-dot w-2 h-2 bg-gray-400 rounded-full inline-block" />
              <span className="typing-dot w-2 h-2 bg-gray-400 rounded-full inline-block" />
              <span className="typing-dot w-2 h-2 bg-gray-400 rounded-full inline-block" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-3 border-t border-gray-200 bg-gray-50">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Ask about Colorado trails..."
            className="flex-1 px-4 py-2.5 rounded-xl border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent bg-white"
            disabled={isLoading}
          />
          <button
            onClick={() => {
              const SpeechRecognition = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
              if (!SpeechRecognition) {
                alert("Speech recognition is not supported in this browser.");
                return;
              }
              if (isListening && recognitionRef.current) {
                recognitionRef.current.stop();
                setIsListening(false);
                return;
              }
              const recognition = new SpeechRecognition();
              recognition.lang = "en-US";
              recognition.interimResults = false;
              recognition.maxAlternatives = 1;
              recognition.onresult = (event: any) => {
                const transcript = event.results[0][0].transcript;
                setInput((prev) => (prev ? prev + " " + transcript : transcript));
                setIsListening(false);
              };
              recognition.onerror = () => setIsListening(false);
              recognition.onend = () => setIsListening(false);
              recognitionRef.current = recognition;
              recognition.start();
              setIsListening(true);
            }}
            className={`p-2.5 rounded-xl transition-colors ${
              isListening
                ? "bg-red-500 text-white animate-pulse"
                : "bg-gray-200 text-gray-600 hover:bg-gray-300"
            }`}
            title={isListening ? "Stop listening" : "Voice input"}
          >
            {isListening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
          </button>
          <button
            onClick={async () => {
              setItineraryLoading(true);
              setMessages((prev) => [...prev, { role: "user", content: "Build me a 3-day hiking itinerary" }]);
              try {
                const res = await generateItinerary(3);
                setMessages((prev) => [...prev, { role: "assistant", content: res.itinerary }]);
              } catch {
                setMessages((prev) => [...prev, { role: "assistant", content: "Failed to generate itinerary." }]);
              }
              setItineraryLoading(false);
            }}
            disabled={isLoading || itineraryLoading}
            className="p-2.5 rounded-xl bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            title="Build Itinerary"
          >
            <Calendar className="w-5 h-5" />
          </button>
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            className="p-2.5 rounded-xl bg-emerald-700 text-white hover:bg-emerald-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}
/* accessibility: improved focus styles */
