# The Lenny Growth Assistant - Backend Service

FastAPI asynchronous backend powering The Lenny Growth Assistant workbench. Grounded in *Lenny's Podcast & Newsletter* transcripts with hybrid dense/sparse vector retrieval, multi-model switching, and sandboxed artifact streaming.

---

## Architecture Overview

- **Framework**: FastAPI with Python 3.12+ and `uv` package management.
- **Data Access**: Async SQLAlchemy 2.0 supporting SQLite (via `aiosqlite`) and PostgreSQL (via `asyncpg`).
- **Vector Search**: Qdrant Vector Database with FastEmbed hybrid dense (`BAAI/bge-base-en-v1.5`) and sparse (`SPLADE++`) embedding models.
- **Model Providers**: Unified `BaseLLMClient` supporting Anthropic Claude, OpenAI, Google Gemini, and Local Ollama.
- **Streaming**: Server-Sent Events (SSE) streaming tokens, structured citations, and isolated artifact blocks.

---

## Getting Started

### 1. Prerequisites
- Python 3.12+ with `uv` installed
- (Optional) Qdrant running on `http://localhost:6333`
- (Optional) Ollama running on `http://localhost:11434`

### 2. Installation and Setup
```bash
# Install dependencies
uv sync

# Ingest and index transcripts into Qdrant
uv run python -m app.scripts.ingest

# Start development server
uv run uvicorn main:app --reload --port 8000
```

### 3. Running Automated Tests
```bash
uv run pytest
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | Runtime environment (`development`, `production`, `testing`) |
| `DATABASE_URL` | `sqlite+aiosqlite:///./lenny_assistant.db` | Database connection URL |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant vector database URL |
| `QDRANT_COLLECTION_NAME` | `lenny_transcripts` | Collection name for transcript chunks |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Local Ollama daemon URL |
| `OLLAMA_MODEL` | `llama3.2` | Default local model |
| `ANTHROPIC_API_KEY` | None | Anthropic Claude API key |
| `OPENAI_API_KEY` | None | OpenAI API key |
| `GEMINI_API_KEY` | None | Google Gemini API key |
| `CORS_ORIGINS` | `["http://localhost:3000","http://127.0.0.1:3000","http://localhost:5173","https://bhaveshupadhyay.github.io","https://lennyai.clientmanger.tech"]` | Allowed CORS origins |
| `CORS_ORIGIN_REGEX` | `"https?://.*(clientmanger\\.tech\|github\\.io\|vercel\\.app\|onrender\\.com)"` | Allowed CORS origin regex |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
