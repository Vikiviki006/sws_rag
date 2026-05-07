import { useState, useRef, useEffect } from "react";
import { SendHorizonal } from "lucide-react";

export default function ChatInput({ onSend, disabled }) {
  const [text, setText] = useState("");
  const textareaRef = useRef(null);

  const handleSend = () => {
    if (text.trim() && !disabled) {
      onSend(text.trim());
      setText("");
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [text]);

  return (
    <div className="relative max-w-3xl mx-auto w-full group">
      <div className="absolute -inset-0.5 bg-gradient-to-r from-signal-600/20 to-purple-600/20 rounded-2xl blur opacity-75 group-hover:opacity-100 transition duration-1000 group-hover:duration-200"></div>
      <div className="relative flex items-end gap-2 bg-ink-900 border border-ink-700 rounded-2xl p-2 focus-within:border-signal-600/50 transition-all">
        <textarea
          ref={textareaRef}
          rows={1}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about leave, WFH, IT security..."
          disabled={disabled}
          className="flex-1 bg-transparent border-none focus:ring-0 text-slate-200 text-sm py-2 px-3 resize-none max-h-[200px] placeholder:text-slate-600"
        />
        <button
          onClick={handleSend}
          disabled={!text.trim() || disabled}
          className="p-2 rounded-xl bg-signal-600 text-white disabled:bg-ink-800 disabled:text-slate-600 transition-all hover:bg-signal-500 flex-shrink-0"
        >
          <SendHorizonal size={18} />
        </button>
      </div>
    </div>
  );
}
