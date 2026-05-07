# PolicyAI — RAG-Powered Company Policy Chatbot

> A fully local, production-grade RAG chatbot that answers employee questions from internal policy PDFs using **deepseek-coder-v2:16b**, **ChromaDB**, and a **React** frontend.

---

## Architecture

```
PDF Documents
    │
    ▼
Document Loader (PyPDF)
    │
    ▼
RecursiveCharacterTextSplitter (chunk_size=500, overlap=50)
    │
    ▼
OllamaEmbeddings (nomic-embed-text → 768-dim vectors)
    │
    ▼
ChromaDB (HNSW index, persisted to disk)
    │
    ▼ (at query time)
Semantic Retriever (MMR, top_k=4)
    │
    ▼
Prompt Template (context-constrained)
    │
    ▼
deepseek-coder-v2:16b (via Ollama, local)
    │
    ▼
Grounded Answer + Source Citations
    │
    ▼
FastAPI REST API → React Chat UI
```

---

## Prerequisites

| Tool | Install | Version |
|------|---------|---------|
| Python | [python.org](https://python.org) | 3.10+ |
| Node.js | [nodejs.org](https://nodejs.org) | 18+ |
| Ollama | [ollama.com](https://ollama.com) | Latest |

---

## Quick Start

### 1. Install Ollama models

```bash
ollama pull deepseek-coder-v2:16b
ollama pull nomic-embed-text
```

Verify both are available:
```bash
ollama list
```

---

### 2. Backend setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env .env.local             # edit if needed (ports, model names)
```

---

### 3. Ingest policy documents

Place your PDF files in `backend/uploads/`:

```
backend/uploads/
├── HR Policy.pdf
├── Leave Policy.pdf
├── WFH Policy.pdf
├── Resignation Policy.pdf
├── IT Security Policy.pdf
└── Benefits Policy.pdf
```

Run the ingestion pipeline:

```bash
cd backend
python ingest.py
```

Expected output:
```
  ✓ HR Policy.pdf — 42 chunks
  ✓ Leave Policy.pdf — 31 chunks
  ...
Total chunks in vectorstore: 198
```

---

### 4. Start the backend

```bash
cd backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

API docs available at: http://localhost:8000/docs

---

### 5. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open: **http://localhost:3000**

---

## API Reference

### `POST /api/chat`

Ask a question from the RAG pipeline.

**Request:**
```json
{
  "question": "What is the annual leave entitlement?"
}
```

**Response:**
```json
{
  "answer": "Employees are entitled to 18 days of annual leave per year...",
  "sources": ["Leave Policy.pdf"]
}
```

---

### `POST /api/upload`

Upload a PDF for automatic ingestion.

```bash
curl -X POST http://localhost:8000/api/upload \
  -F "file=@Leave_Policy.pdf"
```

**Response:**
```json
{
  "filename": "Leave_Policy.pdf",
  "chunks_added": 31,
  "status": "success",
  "message": "Successfully ingested 31 chunks from Leave_Policy.pdf"
}
```

---

### `GET /api/health`

```json
{
  "status": "ok",
  "vectorstore_stats": {
    "total_chunks": 198,
    "collection": "company_policies"
  },
  "models": {
    "llm": "deepseek-coder-v2:16b",
    "embedding": "nomic-embed-text",
    "ollama_url": "http://localhost:11434"
  }
}
```

---

## Architectural Decisions

### Why RAG instead of fine-tuning?

Fine-tuning permanently encodes knowledge into model weights. For company policies this is problematic:

1. **Policies change** — annual leave, WFH rules, notice periods update frequently. RAG lets you re-ingest a PDF and changes are instantly reflected. Fine-tuning requires a full retraining cycle.
2. **Hallucination risk** — fine-tuned models confidently generate answers even outside their training distribution. RAG constrains the LLM to only what was retrieved.
3. **Auditability** — every answer cites the source PDF so HR can verify and trace back claims.
4. **Cost** — fine-tuning a 16B model requires significant GPU time. RAG is incremental.

### Why ChromaDB?

ChromaDB is an embedded vector database that stores embeddings locally as SQLite + HNSW index files:
- **Zero infrastructure** — no Docker, no network calls, no API keys
- **Private** — all data stays on your machine (critical for internal HR docs)
- **Fast** — HNSW approximate nearest-neighbour search at sub-millisecond latency for thousands of chunks
- **Persistent** — survives server restarts without reimporting

### Why chunk_overlap=50?

Text is split at arbitrary character boundaries. A sentence explaining "employees get 18 leave days" might be cut across two chunks. With overlap=50, the boundary content appears in BOTH adjacent chunks. This prevents the retriever from missing context that straddles a split point. Think of it as a sliding window, not a hard cut.

### Why RecursiveCharacterTextSplitter?

It respects natural language hierarchy: tries to split on `\n\n` (paragraphs), then `\n` (lines), then `.` (sentences), then spaces, before falling back to character splits. This produces semantically coherent chunks vs naive fixed-length character splitting.

### How semantic retrieval works

1. User query is embedded using the same `nomic-embed-text` model used during ingestion.
2. ChromaDB performs HNSW nearest-neighbour search in 768-dimensional embedding space.
3. "Semantic" means conceptually similar text ranks high even with zero keyword overlap — "days off" retrieves "annual leave entitlement".
4. **MMR (Maximal Marginal Relevance)** diversifies results — instead of 4 near-identical chunks from the same paragraph, it balances relevance and diversity for broader context coverage.

### How source grounding prevents hallucinations

The prompt template contains a hard constraint:
```
"Answer ONLY using the context below. If not found, respond:
'I don't have that information in the company documents.'"
```

The LLM receives only the retrieved text as its knowledge base. It has no reason to invent facts because the ground truth is explicitly provided. Source filenames are attached to every response for UI-level auditability.

---

## Project Structure

```
rag-policy-chatbot/
├── backend/
│   ├── app.py              ← FastAPI endpoints (thin HTTP adapter)
│   ├── ingest.py           ← PDF load → chunk → embed → ChromaDB
│   ├── rag.py              ← Retrieval + generation pipeline
│   ├── requirements.txt
│   ├── .env
│   ├── vectorstore/        ← ChromaDB persisted data (auto-created)
│   ├── uploads/            ← Drop PDFs here before ingestion
│   └── utils/
│       ├── __init__.py
│       ├── config.py       ← Pydantic Settings (env vars)
│       └── logger.py       ← Structured logging
│
├── frontend/
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── package.json
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── index.css
│       ├── components/
│       │   ├── ChatInput.jsx       ← Textarea + send button
│       │   ├── MessageBubble.jsx   ← User/assistant message rendering
│       │   ├── SourceBadge.jsx     ← Source citation pill
│       │   ├── Loader.jsx          ← Typing indicator dots
│       │   └── UploadPanel.jsx     ← Drag-and-drop PDF uploader
│       ├── pages/
│       │   └── ChatPage.jsx        ← Main layout + state management
│       └── services/
│           └── api.js              ← Axios API calls
│
├── README.md
└── .env
```

---

## Troubleshooting

**Ollama not responding**
```bash
# Check Ollama is running
ollama serve
```

**Model not found**
```bash
ollama pull deepseek-coder-v2:16b
ollama pull nomic-embed-text
```

**Empty vectorstore (no answers)**
```bash
cd backend && python ingest.py
```

**CORS errors in browser**
Ensure `ALLOWED_ORIGINS` in `.env` includes `http://localhost:3000`.

**Slow responses**
deepseek-coder-v2:16b is a 16B parameter model. On CPU it takes 30-120s per response. For faster inference use a GPU or switch to `deepseek-coder:6.7b` in `.env`.
