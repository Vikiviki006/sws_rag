import { FileText } from "lucide-react";

export default function SourceBadge({ source }) {
  return (
    <div className="flex items-center gap-1 px-2 py-0.5 rounded-md bg-ink-700/50 border border-ink-600 text-[10px] text-slate-400 font-medium">
      <FileText size={10} className="text-signal-400" />
      <span className="truncate max-w-[120px]">{source}</span>
    </div>
  );
}
