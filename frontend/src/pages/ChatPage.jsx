/**
 * ChatPage — the primary view.
 *
 * Layout:
 *   ┌─────────────────────────────────────────┐
 *   │  Header (logo + upload button + status)  │
 *   ├─────────────────────────────────────────┤
 *   │                                         │
 *   │           Message list                  │
 *   │                                         │
 *   ├─────────────────────────────────────────┤
 *   │  Suggested questions (initial state)    │
 *   │  ChatInput                              │
 *   └─────────────────────────────────────────┘
 */

import { useState, useEffect, useRef } from "react";
import {
  Bot,
  Upload,
  Database,
  Activity,
  AlertTriangle,
  Sparkles,
} from "lucide-react";
import MessageBubble from "../components/MessageBubble";
import ChatInput from "../components/ChatInput";
import Loader from "../components/Loader";
import UploadPanel from "../components/UploadPanel";
import { sendChatMessage, fetchHealth } from "../services/api";

const SUGGESTED = [
  "What is the annual leave entitlement?",
  "How many WFH days are allowed per week?",
  "What is the notice period for resignation?",
  "What IT security rules apply to remote work?",
  "What are the employee benefits offered?",
  "How do I apply for sick leave?",
];

export default function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [health, setHealth] = useState(null);
  const [healthError, setHealthError] = useState(false);
  const bottomRef = useRef(null);

  // Fetch health on mount
  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch(() => setHealthError(true));
  }, []);

  // Auto-scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  async function handleSend(question) {
    const userMsg = {
      id: Date.now(),
      role: "user",
      content: question,
      sources: [],
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const { answer, sources } = await sendChatMessage(question);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: "assistant",
          content: answer,
          sources,
          timestamp: new Date(),
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: "assistant",
          content: `⚠️ Error: ${err.message}`,
          sources: [],
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  function handleUploadSuccess() {
    // Re-fetch health to show updated chunk count
    fetchHealth().then(setHealth).catch(() => {});
  }

  const chunks = health?.vectorstore_stats?.total_chunks ?? null;

  return (
    <div className="h-screen flex flex-col bg-ink-950 font-sans">
      {/* ── Header ───────────────────────────────────────────────────── */}
      <header className="flex-shrink-0 flex items-center justify-between px-5 py-3.5 bg-ink-900 border-b border-ink-700">
        <div className="flex items-center gap-3">
          {/* Logo mark */}
          <div className="w-8 h-8 rounded-lg bg-signal-600 flex items-center justify-center">
            <Bot size={18} className="text-white" />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-slate-100 leading-none">PolicyAI</h1>
            <p className="text-xs text-slate-500 mt-0.5">Company Policy Assistant</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Vectorstore pill */}
          {health && !healthError && (
            <div className="hidden sm:flex items-center gap-1.5 text-xs text-slate-500 bg-ink-800 border border-ink-700 rounded-full px-3 py-1.5">
              <Database size={12} className="text-signal-400" />
              <span>{chunks !== null ? `${chunks} chunks indexed` : "Indexing…"}</span>
            </div>
          )}
          {healthError && (
            <div className="flex items-center gap-1.5 text-xs text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-full px-3 py-1.5">
              <AlertTriangle size={12} />
              <span>Backend offline</span>
            </div>
          )}

          {/* Status dot */}
          <div className="flex items-center gap-1.5 text-xs text-emerald-400">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="hidden sm:inline">Live</span>
          </div>

          {/* Upload button */}
          <button
            onClick={() => setShowUpload(true)}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-medium
              bg-signal-600/20 border border-signal-600/30 text-signal-400
              hover:bg-signal-600/30 transition-all"
          >
            <Upload size={13} />
            <span>Upload PDF</span>
          </button>
        </div>
      </header>

      {/* ── Message area ─────────────────────────────────────────────── */}
      <main className="flex-1 overflow-y-auto px-4 py-6 space-y-5">
        {/* Empty state */}
        {messages.length === 0 && !isLoading && (
          <div className="flex flex-col items-center justify-center h-full gap-6 pb-10">
            <div className="flex flex-col items-center gap-3 text-center">
              <div className="w-14 h-14 rounded-2xl bg-ink-800 border border-ink-700 flex items-center justify-center">
                <Sparkles size={24} className="text-signal-400" />
              </div>
              <h2 className="text-lg font-semibold text-slate-200">
                Ask me about company policies
              </h2>
              <p className="text-sm text-slate-500 max-w-xs">
                I'll answer from your uploaded HR, leave, WFH, and other policy documents. No guessing — only what's in the docs.
              </p>
            </div>

            {/* Suggested questions */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-xl">
              {SUGGESTED.map((q) => (
                <button
                  key={q}
                  onClick={() => handleSend(q)}
                  className="text-left text-sm px-4 py-3 rounded-xl bg-ink-800 border border-ink-700
                    text-slate-400 hover:text-slate-200 hover:border-ink-600 hover:bg-ink-700
                    transition-all duration-150"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Message list */}
        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            role={msg.role}
            content={msg.content}
            sources={msg.sources}
            timestamp={msg.timestamp}
          />
        ))}

        {/* Typing indicator */}
        {isLoading && (
          <div className="flex gap-3 animate-fade-up">
            <div className="w-8 h-8 rounded-full bg-ink-700 border border-ink-600 flex items-center justify-center text-signal-400 flex-shrink-0">
              <Bot size={15} />
            </div>
            <div className="bg-ink-800 border border-ink-700 rounded-2xl rounded-tl-sm">
              <Loader />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </main>

      {/* ── Input bar ────────────────────────────────────────────────── */}
      <footer className="flex-shrink-0 px-4 pb-4 pt-2">
        <ChatInput onSend={handleSend} disabled={isLoading} />
        <p className="text-center text-xs text-slate-700 mt-2">
          Answers grounded in uploaded policy documents · Powered by{" "}
          <span className="text-slate-600">deepseek-coder-v2 + ChromaDB</span>
        </p>
      </footer>

      {/* ── Upload modal ─────────────────────────────────────────────── */}
      {showUpload && (
        <UploadPanel
          onClose={() => setShowUpload(false)}
          onSuccess={handleUploadSuccess}
        />
      )}
    </div>
  );
}
