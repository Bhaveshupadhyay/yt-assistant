# System Architecture Specification
## Project: The Lenny Growth Assistant
**Author:** Forward Deployed Engineer (FDE)  
**Version:** 1.0.0  

---

## 1. High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       CLIENT LAYER                                          │
│                                                                                             │
│  ┌──────────────────────────────────────────────┬────────────────────────────────────────┐  │
│  │             Conversational UI                │         Sandboxed Artifact Viewer      │  │
│  │  - Session History & New Chat Drawer         │  - Side-by-Side Split View             │  │
│  │  - Streaming Chat Feed (SSE)                 │  - Isolated <iframe> (No parent DOM)   │  │
│  │  - Expandable Citation Badges                │  - Preview / Raw Code Tab Switching    │  │
│  │  - Cloud ↔ Local Ollama Toggle Switch        │  - One-Click Copy & Export             │  │
│  └──────────────────────────────────────────────┴────────────────────────────────────────┘  │
└──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                               │ (HTTP / Server-Sent Events)
                                               ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    FASTAPI BACKEND LAYER                                    │
│                                                                                             │
│  ┌─────────────────┐     ┌─────────────────────┐     ┌───────────────────────────────────┐  │
│  │   API Routers   │ ──► │   Service Layer     │ ──► │     Model Provider Router         │  │
│  │  /api/v1/chat   │     │  - RAGService       │     │  ┌──────────────┬──────────────┐  │  │
│  │  /api/v1/session│     │  - Ship30Service    │     │  │ Cloud LLM    │ Local LLM    │  │  │
│  │  /api/v1/models │     │  - ArtifactService  │     │  │ (Anthropic/  │ (Ollama on   │  │  │
│  │  /health        │     │  - SessionService   │     │  │  OpenAI)     │  11434)      │  │  │
│  └─────────────────┘     └──────────┬──────────┘     │  └──────────────┴──────────────┘  │  │
│                                     │                └───────────────────────────────────┘  │
│                                     ▼                                                       │
│                          ┌─────────────────────┐                                            │
│                          │  Repository Layer   │                                            │
│                          │  (SQLAlchemy 2.0)   │                                            │
│                          └──────────┬──────────┘                                            │
└─────────────────────────────────────┼───────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                     PERSISTENCE LAYER                                       │
│                                                                                             │
│  ┌──────────────────────────────────────────────┬────────────────────────────────────────┐  │
│  │           PostgreSQL Database                │             Vector Knowledge Base      │  │
│  │  - chat_sessions (UUID, title, timestamps)   │  - Ingested Lenny Podcast Transcripts  │  │
│  │  - messages (role, content, citations, json) │  - Chunk embeddings (BGE / nomic / all)│  │
│  │  - artifacts (type, title, html/md payload)  │  - Metadata: Guest, Episode, Timestamp │  │
│  └──────────────────────────────────────────────┴────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Database Schema (PostgreSQL)

```sql
-- 1. Chat Sessions Table
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL DEFAULT 'New Conversation',
    model_used VARCHAR(100) NOT NULL DEFAULT 'claude-3-5-sonnet',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Messages Table
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    citations JSONB DEFAULT '[]'::jsonb,
    has_artifact BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Artifacts Table
CREATE TABLE artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    artifact_type VARCHAR(50) NOT NULL CHECK (artifact_type IN ('html', 'markdown', 'svg')),
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_artifacts_session_id ON artifacts(session_id);
```

---

## 3. RAG & Transcript Ingestion Flow

```
[Raw Transcripts] ──► [Cleaning & Metadata Extraction] ──► [Semantic Chunking]
(Lenny Archive)       - Title, Guest, Topic, URL           - 600 tokens / 100 overlap
                                                                   │
                                                                   ▼
[Vector Store / Index] ◄── [Embedding Generation] ◄────────────────┘
                           (FastEmbed / SentenceTransformers / Ollama)
```

### Chunking & Retrieval Parameters:
- **Chunk Size:** 500–700 tokens (~2,000 characters).
- **Chunk Overlap:** 100 tokens to preserve conversational context across boundaries.
- **Metadata Fields:** `episode_title`, `guest_name`, `guest_role`, `youtube_url`, `timestamp_start`.
- **Top-K Retrieval:** Top 3–5 chunks retrieved per user query using cosine similarity.
- **Grounding Threshold:** Chunks with similarity `< 0.65` are flagged, triggering the zero-hallucination fallback if no relevant context exists.

---

## 4. Flexible Model Provider Layer (Cloud ↔ Ollama)

The backend provides a unified `BaseLLMClient` interface that standardizes completion and streaming across providers:

```python
class BaseLLMClient(ABC):
    @abstractmethod
    async def astream_chat(
        self,
        messages: list[dict[str, str]],
        system_prompt: str
    ) -> AsyncGenerator[str, None]:
        pass
```

### Active Implementations:
1. **`AnthropicClient` / `OpenAIClient`:** Cloud execution with high fidelity and rapid streaming.
2. **`OllamaClient`:** Local offline execution against `http://localhost:11434` (e.g. `llama3.2:3b`, `mistral:7b`, or `qwen2.5:7b`).
3. **Resilience & Fallback:** If Ollama daemon is unreachable, the system raises `OllamaUnavailableException` with fallback instructions rather than crashing.

---

## 5. Dedicated "Ship 30 for 30" Skill Engine

When triggered (via prompt intent or UI action), the assistant activates a dedicated system prompt pipeline encoding:
1. **Hook Strategy:** Contrarian truth or high-stakes problem framing.
2. **Structure:** 1-3-1 sentence cadence with short, digestible paragraphs.
3. **Typography:** Selective bolding on first 2–4 words of key bullet points.
4. **Volume:** Target ~1,250 words with zero fluff.
5. **Grounded Attribution:** Incorporating specific quotes from Lenny's guests.

---

## 6. Security Sandbox & Artifact Isolation Model

To guarantee safe execution of user-generated and LLM-generated HTML/CSS/JS:

```
┌────────────────────────────────────────────────────────┐
│ Main Application Window (React / Next.js)              │
│ - No direct innerHTML injection of untrusted code      │
│                                                        │
│   ┌────────────────────────────────────────────────┐   │
│   │ Sandboxed <iframe> Container                   │   │
│   │   sandbox="allow-scripts"                      │   │
│   │   (Explicitly DISALLOWS allow-same-origin,     │   │
│   │    allow-top-navigation, allow-forms)          │   │
│   │                                                │   │
│   │   CSP Meta Tag Injected in srcdoc:             │   │
│   │   default-src 'self' 'unsafe-inline';          │   │
│   │   script-src 'unsafe-inline';                  │   │
│   │   connect-src 'none';                          │   │
│   └────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────┘
```

* **Isolation:** The iframe runs in a unique origin (`null`), preventing access to host `localStorage`, session cookies, or parent window DOM.
* **Network Blocking:** CSP `connect-src 'none'` prevents generated scripts from making unauthorized external network requests.

---

## 7. API Endpoint Contracts

| Method | Endpoint | Description | Request Body | Response Body |
|---|---|---|---|---|
| `GET` | `/health` | Health & provider liveness | - | `{"status": "ok", "db": true, "ollama": true}` |
| `GET` | `/api/v1/models` | List available models | - | `{"active": "claude-3-5", "available": [...]}` |
| `POST` | `/api/v1/sessions` | Create new chat session | `{"title": "Pricing"}` | `SessionRead` |
| `GET` | `/api/v1/sessions` | List recent sessions | - | `list[SessionRead]` |
| `GET` | `/api/v1/sessions/{id}`| Get session history | - | `SessionDetail` |
| `POST` | `/api/v1/chat` | Stream SSE chat response | `ChatRequest` | `text/event-stream` (tokens, citations, artifacts) |

---

## 8. Deployment Topology (Docker Compose)

```yaml
version: '3.8'
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: lenny_assistant
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:password@postgres:5432/lenny_assistant
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      OLLAMA_BASE_URL: http://host.docker.internal:11434
    depends_on:
      - postgres

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend

volumes:
  pgdata:
```
