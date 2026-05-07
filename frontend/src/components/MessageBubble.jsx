import { Bot, User, Clock } from "lucide-react";
import SourceBadge from "./SourceBadge";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export default function MessageBubble({ role, content, sources, timestamp }) {
  const isBot = role === "assistant";
  
  return (
    <div className={cn("flex gap-3 animate-fade-up w-full", isBot ? "justify-start" : "justify-end")}>
      {isBot && (
        <div className="w-8 h-8 rounded-full bg-ink-700 border border-ink-600 flex items-center justify-center text-signal-400 flex-shrink-0">
          <Bot size={15} />
        </div>
      )}
      
      <div className={cn(
        "max-w-[85%] sm:max-w-[70%] flex flex-col gap-2",
        !isBot && "items-end"
      )}>
        <div className={cn(
          "px-4 py-3 rounded-2xl text-sm leading-relaxed",
          isBot 
            ? "bg-ink-800 border border-ink-700 text-slate-200 rounded-tl-sm" 
            : "bg-signal-600 text-white rounded-tr-sm"
        )}>
          <div className="whitespace-pre-wrap">{content}</div>
          
          {isBot && sources && sources.length > 0 && (
            <div className="mt-3 pt-3 border-t border-ink-700 flex flex-wrap gap-1.5">
              {sources.map((src, idx) => (
                <SourceBadge key={idx} source={src} />
              ))}
            </div>
          )}
        </div>
        
        <div className="flex items-center gap-1.5 px-1 text-[10px] text-slate-600">
          <Clock size={10} />
          <span>{new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
        </div>
      </div>

      {!isBot && (
        <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-white flex-shrink-0">
          <User size={15} />
        </div>
      )}
    </div>
  );
}
