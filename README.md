# The Lenny Growth Assistant

> **Forward Deployed Engineer (FDE) Technical Assignment Submission**  
> An enterprise conversational AI workbench grounded strictly in *Lenny's Podcast & Newsletter* transcripts, featuring verifiable guest attribution, multi-session persistence, flexible LLM toggling (Anthropic Claude, OpenAI, Google Gemini, and Local Ollama), Ship 30 for 30 atomic essay generation, and a sandboxed side-by-side artifact viewer.

---

## Deliverables and Documentation

| Document | Description |
|---|---|
| [**`PRD.md`**](./PRD.md) | **Product Requirements Document**: User personas, problem statement, success metrics, assumptions, in/out-of-scope boundaries, and risk mitigation. |
| [**`architecture.md`**](./architecture.md) | **System Architecture**: PostgreSQL/SQLite schema, FastAPI Clean Architecture, RAG chunking & retrieval, multi-provider model routing, and iframe sandbox security. |
| [**`design.md`**](./design.md) | **UI/UX Design Specification**: Split-screen workbench layout, interaction states (streaming, citations, artifacts), accessibility, and design tokens. |
| [**`SKILL.md`**](file:///Users/bhaveshupadhyay/IdeaProjects/yt-assistant/.agents/skills/lenny-growth-assistant/SKILL.md) | **AI Agent Skill**: Operational domain rules, citation requirements, and Ship 30 for 30 writing standards. |

---

## Core Features

1. **Strict Transcript Grounding (RAG)**: Answers tactical product and growth questions using *Lenny's Podcast* transcripts with verifiable guest attribution (e.g., Elena Verna, Brian Balfour, Shreyas Doshi, Casey Winters). Features high-precision hybrid retrieval (Dense BGE-base-en-v1.5 + Sparse SPLADE via FastEmbed and Qdrant) with a strict zero-hallucination fallback.
2. **Dedicated "Ship 30 for 30" Essay Engine**: Synthesizes deep transcript insights into ~1,250-word atomic essays featuring magnetic contrarian hooks, 1-3-1 sentence pacing, visual bolding, and actionable 3-step closing checklists.
3. **Claude-Style In-App Artifact Viewer**: Renders interactive HTML/CSS/JS applications, calculators, checklists, and formatted Markdown strategy memos side-by-side with chat.
4. **Untrusted Code Security Sandbox**: Isolated `<iframe>` execution container with strict Content Security Policy (`connect-src 'none'`, `sandbox="allow-scripts"`) preventing parent DOM access, cookie leakage, or unauthorized external network requests.
5. **Flexible Multi-Model Architecture**: Seamlessly switch between Enterprise Cloud LLMs (Anthropic Claude 3.5/3.7 Sonnet, OpenAI GPT-4o/4o-mini, Google Gemini 3.6/3.7) and **100% Offline Local LLMs (Ollama Llama 3.2, Mistral, Qwen 2.5, DeepSeek R1)** with automatic daemon health detection.
6. **Multi-Session Persistence**: Async relational database persistence (SQLite with aiosqlite or PostgreSQL with asyncpg) storing chat sessions, message histories, timestamps, citation metadata, and generated artifacts.

---

## Technical Stack

- **Backend**: Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (Async), `uv` package manager.
- **Vector Retrieval**: Qdrant vector database with FastEmbed dense (`BAAI/bge-base-en-v1.5`) and sparse (`SPLADE++`) embedding models.
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Lucide React icons.
- **Containerization**: Docker, Docker Compose.

---

## Quickstart and Development

### 1. One-Command Docker Deployment
The quickest way to run the entire stack (Frontend, Backend, and Qdrant Vector Store):

```bash
docker compose up --build
```

- **Frontend Workbench**: `http://localhost:5173` (or `http://localhost:3000`)
- **Backend API Docs**: `http://localhost:8000/docs`
- **Qdrant Dashboard**: `http://localhost:6333/dashboard`

---

### 2. Local Development Setup

#### Prerequisites
- Python 3.12+ with [`uv`](https://github.com/astral-sh/uv) installed
- Node.js 18+ and `npm`
- (Optional) Local [Ollama](https://ollama.ai) daemon running on `http://localhost:11434`
- (Optional) Qdrant running on `http://localhost:6333` (or start via `docker run -p 6333:6333 qdrant/qdrant`)

#### Backend Setup
```bash
# Navigate to backend directory
cd backend

# Install dependencies using uv
uv sync

# Run transcript ingestion and vector indexing
uv run python -m app.scripts.ingest

# Start FastAPI development server
uv run uvicorn main:app --reload --port 8000
```

#### Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install npm packages
npm install

# Start Vite development server
npm run dev
```

The frontend will be available at `http://localhost:5173` with automatic API proxying to `http://localhost:8000`.

---

### 3. Running Automated Tests

```bash
cd backend
uv run pytest
```

---

## Environment Variables Configuration

Create a `.env` file in the root directory (or copy from `.env.example`):

```env
# Application Settings
ENVIRONMENT=development
LOG_LEVEL=INFO
DEBUG=false

# Database Configuration
DATABASE_URL=sqlite+aiosqlite:///./lenny_assistant.db

# Vector Database (Qdrant)
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=lenny_transcripts

# Local Model (Ollama)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Cloud Model API Keys (Optional for Cloud Execution)
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# Frontend CORS
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000","http://localhost:5173"]
```

---

## Project Structure

```text
.
├── PRD.md                         # Product Requirements Document
├── README.md                      # Project Overview and Quickstart
├── architecture.md                # System Architecture and DB Schema
├── design.md                      # UI/UX Design System Specifications
├── docker-compose.yml             # Containerized multi-service deployment
├── backend/                       # FastAPI async backend
│   ├── app/
│   │   ├── api/v1/                # Route controllers (chat, sessions, models, health)
│   │   ├── core/                  # App config, database, enums, exceptions, logging
│   │   ├── models/                # SQLAlchemy database models & Pydantic schemas
│   │   ├── repositories/          # Data access layer
│   │   ├── services/              # Business logic (RAG, Chat, Artifacts, Ship30, LLMs)
│   │   └── scripts/               # Transcript ingestion and indexing pipeline
│   ├── tests/                     # Unit and integration test suite
│   ├── Dockerfile                 # Backend container definition
│   └── pyproject.toml             # Python dependencies and metadata
├── frontend/                      # React + TypeScript + Vite frontend
│   ├── src/                       # Components, hooks, services, types
│   ├── Dockerfile                 # Frontend production build container
│   └── package.json               # Frontend dependencies and scripts
└── data/
    └── transcripts/               # Raw and curated podcast transcript files
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | System health check, database status, and Ollama connectivity |
| `GET` | `/api/v1/models` | List all available and active LLM providers |
| `GET` | `/api/v1/sessions` | List recent conversation sessions |
| `POST` | `/api/v1/sessions` | Create a new conversation session |
| `GET` | `/api/v1/sessions/{id}` | Retrieve message history and artifacts for a session |
| `DELETE` | `/api/v1/sessions/{id}` | Delete a conversation session |
| `POST` | `/api/v1/chat` | Stream conversational SSE responses with citations and artifacts |

---

## Security and Sandboxing

- **Zero Untrusted Execution**: Generated HTML, CSS, and JavaScript widgets are isolated in an `<iframe>` container with `sandbox="allow-scripts"`.
- **Content Security Policy**: The iframe enforces `connect-src 'none'`, preventing unauthorized network requests, cookie exfiltration, or access to parent window storage.
- **Input Sanitization**: User and model inputs are strictly typed and validated via Pydantic v2 schemas.
