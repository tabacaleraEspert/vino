import { useState, useRef, useEffect } from "react";
import { Send, Sparkles, User, Loader2 } from "lucide-react";
import { apiFetch } from "../../lib/api";
import { useMonth } from "../context/MonthContext";

interface Message {
  id: string;
  role: "user" | "assistant";
  text: string;
  timestamp: Date;
}

export function Chat() {
  const { selectedMonth } = useMonth();
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      text: "Hola! Soy tu asistente financiero. Preguntame lo que quieras sobre tus gastos, presupuestos, o si podes comprar algo.\n\nEjemplos:\n- _Puedo comprarme unas zapatillas de 80k?_\n- _Como vengo de presupuesto este mes?_\n- _En que estoy gastando mas?_",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const period = `${selectedMonth.year}-${String(selectedMonth.month + 1).padStart(2, "0")}`;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isLoading) return;

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      text,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const res = await apiFetch<{ reply: string }>("/chat/ask", {
        method: "POST",
        body: JSON.stringify({ message: text, period }),
      });

      const assistantMsg: Message = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        text: res.reply,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (e: any) {
      const errorMsg: Message = {
        id: `error-${Date.now()}`,
        role: "assistant",
        text: `Error: ${e.message || "No pude procesar tu consulta"}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-120px)]">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-2.5 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
          >
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                msg.role === "user"
                  ? "bg-blue-600"
                  : "bg-gradient-to-br from-purple-500 to-purple-600"
              }`}
            >
              {msg.role === "user" ? (
                <User className="w-4 h-4 text-white" />
              ) : (
                <Sparkles className="w-4 h-4 text-white" />
              )}
            </div>
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-2.5 ${
                msg.role === "user"
                  ? "bg-blue-600 text-white rounded-br-md"
                  : "bg-white shadow-sm border border-gray-100 rounded-bl-md"
              }`}
            >
              <p
                className={`text-sm whitespace-pre-wrap ${
                  msg.role === "user" ? "text-white" : "text-gray-700"
                }`}
                dangerouslySetInnerHTML={{
                  __html: msg.text
                    .replace(/\*([^*]+)\*/g, "<strong>$1</strong>")
                    .replace(/_([^_]+)_/g, "<em>$1</em>")
                    .replace(/\n/g, "<br/>"),
                }}
              />
              <p
                className={`text-[10px] mt-1 ${
                  msg.role === "user" ? "text-blue-200" : "text-gray-400"
                }`}
              >
                {msg.timestamp.toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" })}
              </p>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-2.5">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-purple-600 flex items-center justify-center flex-shrink-0">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div className="bg-white shadow-sm border border-gray-100 rounded-2xl rounded-bl-md px-4 py-3">
              <div className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 text-purple-500 animate-spin" />
                <span className="text-sm text-gray-500">Pensando...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-3 bg-white border-t border-gray-200">
        <div className="flex items-center gap-2 bg-gray-100 rounded-2xl px-4 py-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Preguntame sobre tus finanzas..."
            className="flex-1 bg-transparent outline-none text-sm"
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="w-9 h-9 bg-purple-600 text-white rounded-xl flex items-center justify-center hover:bg-purple-700 transition-colors disabled:opacity-30"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
