import { useState } from "react";
import { X, Upload, FileText, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { uploadPdf } from "../services/api";

export default function UploadPanel({ onClose, onSuccess }) {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("idle"); // idle, uploading, success, error
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (selected && selected.type === "application/pdf") {
      setFile(selected);
      setError("");
    } else {
      setError("Please select a valid PDF file.");
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    
    setStatus("uploading");
    try {
      const data = await uploadPdf(file);
      setResult(data);
      setStatus("success");
      onSuccess();
    } catch (err) {
      setStatus("error");
      setError(err.message);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="w-full max-w-md bg-ink-900 border border-ink-700 rounded-3xl shadow-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-ink-700">
          <h3 className="text-lg font-semibold text-slate-100">Upload Policy</h3>
          <button onClick={onClose} className="p-1 hover:bg-ink-800 rounded-lg text-slate-500 transition-colors">
            <X size={20} />
          </button>
        </div>

        <div className="p-6">
          {status === "idle" || status === "uploading" ? (
            <div className="space-y-6">
              <label className="group relative flex flex-col items-center justify-center w-full h-40 border-2 border-dashed border-ink-700 rounded-2xl cursor-pointer hover:bg-ink-800/50 hover:border-signal-600/50 transition-all">
                <input type="file" accept=".pdf" onChange={handleFileChange} className="hidden" />
                <div className="flex flex-col items-center gap-2">
                  <div className="p-3 rounded-xl bg-ink-800 text-slate-400 group-hover:text-signal-400 group-hover:scale-110 transition-all">
                    <Upload size={24} />
                  </div>
                  <span className="text-sm text-slate-400 font-medium">
                    {file ? file.name : "Select a policy PDF"}
                  </span>
                  <span className="text-xs text-slate-600">Max size 10MB</span>
                </div>
              </label>

              {error && (
                <div className="flex items-center gap-2 text-xs text-rose-400 bg-rose-500/10 p-3 rounded-xl border border-rose-500/20">
                  <AlertCircle size={14} />
                  <span>{error}</span>
                </div>
              )}

              <button
                onClick={handleUpload}
                disabled={!file || status === "uploading"}
                className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-signal-600 text-white font-medium hover:bg-signal-500 disabled:bg-ink-800 disabled:text-slate-600 transition-all shadow-lg shadow-signal-600/10"
              >
                {status === "uploading" ? (
                  <>
                    <Loader2 size={18} className="animate-spin" />
                    <span>Processing PDF...</span>
                  </>
                ) : (
                  <span>Ingest Document</span>
                )}
              </button>
            </div>
          ) : status === "success" ? (
            <div className="flex flex-col items-center text-center py-4 space-y-4">
              <div className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                <CheckCircle2 size={32} />
              </div>
              <div>
                <h4 className="text-lg font-semibold text-slate-100">Ingestion Successful</h4>
                <p className="text-sm text-slate-500 mt-1">
                  Successfully indexed <strong>{result?.chunks_added}</strong> chunks from <strong>{result?.filename}</strong>.
                </p>
              </div>
              <button
                onClick={onClose}
                className="w-full py-3 rounded-xl bg-ink-800 border border-ink-700 text-slate-300 font-medium hover:bg-ink-700 transition-all"
              >
                Close
              </button>
            </div>
          ) : (
             <div className="flex flex-col items-center text-center py-4 space-y-4">
              <div className="w-16 h-16 rounded-full bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400">
                <AlertCircle size={32} />
              </div>
              <div>
                <h4 className="text-lg font-semibold text-slate-100">Upload Failed</h4>
                <p className="text-sm text-slate-500 mt-1">{error}</p>
              </div>
              <button
                onClick={() => setStatus("idle")}
                className="w-full py-3 rounded-xl bg-signal-600 text-white font-medium hover:bg-signal-500 transition-all"
              >
                Try Again
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
