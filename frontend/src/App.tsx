import { type FormEvent, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import "./App.css";

const API = "http://127.0.0.1:8000";

type Role = "user" | "assistant";
interface Message { role: Role; content: string; }

async function login(email: string, password: string): Promise<string> {
  const res = await fetch(`${API}/auth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error("Invalid credentials");
  const data = await res.json();
  return data.access_token as string;
}

async function sendChat(token: string, message: string): Promise<string> {
  const res = await fetch(`${API}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Request failed: ${res.status}`);
  }
  const data = await res.json();
  return data.answer as string;
}

function LoginForm({ onLogin }: { onLogin: (token: string) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const token = await login(email, password);
      onLogin(token);
    } catch {
      setError("Invalid email or password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-wrap">
      <h1>RAG Chatbot</h1>
      <form className="login-form" onSubmit={handleSubmit}>
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoComplete="email"
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoComplete="current-password"
        />
        {error && <p className="login-error">{error}</p>}
        <button type="submit" disabled={loading}>
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}

function Chat({ token, onLogout }: { token: string; onLogout: () => void }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSend = async (e: FormEvent) => {
    e.preventDefault();
    const message = input.trim();
    if (!message || loading) return;

    setMessages((prev) => [
      ...prev,
      { role: "user", content: message },
      { role: "assistant", content: "…" },
    ]);
    setInput("");
    setLoading(true);

    try {
      const answer = await sendChat(token, message);
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = { role: "assistant", content: answer };
        return updated;
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = { role: "assistant", content: `Error: ${msg}` };
        return updated;
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <div className="chat-header">
        <h1>RAG Chatbot</h1>
        <button className="logout-btn" onClick={onLogout}>Sign out</button>
      </div>
      <div className="single-layout">
        <div className="panel">
          <div className="chat-window">
            {messages.length === 0 && (
              <p className="empty-hint">Ask a question about your documents.</p>
            )}
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
          <form className="input-row" onSubmit={handleSend}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask something…"
              autoComplete="off"
              disabled={loading}
            />
            <button type="submit" disabled={loading}>
              {loading ? "Thinking…" : "Send"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [token, setToken] = useState<string | null>(
    () => sessionStorage.getItem("token")
  );

  const handleLogin = (t: string) => {
    sessionStorage.setItem("token", t);
    setToken(t);
  };

  const handleLogout = () => {
    sessionStorage.removeItem("token");
    setToken(null);
  };

  return token
    ? <Chat token={token} onLogout={handleLogout} />
    : <LoginForm onLogin={handleLogin} />;
}
