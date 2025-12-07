import { type FormEvent, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import "./App.css";

type Role = "user" | "assistant";

interface Message {
  role: Role;
  content: string;
}

const STREAM_URL = "http://127.0.0.1:8000/stream";

async function streamAnswer(
  question: string,
  onChunk: (chunk: string) => void
) {
  const res = await fetch(STREAM_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });

  if (!res.ok || !res.body) {
    throw new Error(`Stream request failed: ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value, { stream: true });
    if (chunk) onChunk(chunk);
  }
}

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);

  const sendMessage = async (e: FormEvent) => {
    e.preventDefault();
    const question = input.trim();
    if (!question || loading) return;

    const userMsg: Message = { role: "user", content: question };
    const assistantMsg: Message = { role: "assistant", content: "" };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setInput("");
    setLoading(true);

    // index of the new assistant message in the updated array
    const assistantIndex = messages.length + 1;

    try {
      await streamAnswer(question, (chunk) => {
        setMessages((prev) => {
          const updated = [...prev];
          const current = updated[assistantIndex];
          if (!current) return prev;
          updated[assistantIndex] = {
            ...current,
            content: current.content + chunk,
          };
          return updated;
        });
      });
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Unknown error occurred";
      setMessages((prev) => {
        const updated = [...prev];
        updated[assistantIndex] = {
          role: "assistant",
          content: `Error: ${message}`,
        };
        return updated;
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <h1>RAG Chatbot</h1>
      <div className="single-layout">
        <div className="panel">
          <div className="chat-window">
            {messages.map((m, i) => (
              <div key={i} className={`msg ${m.role}`}>
                <div className="label">{m.role === "user" ? "You" : "Bot"}</div>
                <div className="bubble">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {m.content}
                  </ReactMarkdown>
                </div>
              </div>
            ))}
          </div>
          <form className="input-row" onSubmit={sendMessage}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask something..."
              autoComplete="off"
            />
            <button type="submit" disabled={loading}>
              {loading ? "Streaming..." : "Send"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default App;
