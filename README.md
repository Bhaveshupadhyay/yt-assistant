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
| [**`SKILL.md`**](./.agents/skills/lenny-growth-assistant/SKILL.md) | **AI Agent Skill**: Operational domain rules, citation requirements, and Ship 30 for 30 writing standards. |

---

## Core Features

1. **Strict Transcript Grounding (RAG)**: Answers tactical product and growth questions using *Lenny's Podcast* transcripts with verifiable guest attribution (e.g., Elena Verna, Brian Balfour, Shreyas Doshi, Casey Winters). Features high-precision hybrid retrieval (Dense BGE-base-en-v1.5 + Sparse SPLADE via FastEmbed and Qdrant) with a strict zero-hallucination fallback.
2. **Dedicated "Ship 30 for 30" Essay Engine**: Synthesizes deep transcript insights into ~1,250-word atomic essays featuring magnetic contrarian hooks, 1-3-1 sentence pacing, visual bolding, and actionable 3-step closing checklists.
3. **Claude-Style In-App Artifact Viewer**: Renders interactive HTML/CSS/JS applications, calculators, checklists, and formatted Markdown strategy memos side-by-side with chat.
4. **Untrusted Code Security Sandbox**: Isolated `<iframe>` execution container (`sandbox="allow-scripts"`, without `allow-same-origin`) executing in an opaque null origin, strictly preventing parent DOM access, cookie theft, local storage leakage, or parent frame navigation.
5. **Flexible Multi-Model Architecture**: Seamlessly switch between Enterprise Cloud LLMs (Anthropic Claude 3.5/3.7 Sonnet, OpenAI GPT-4o/4o-mini, Google Gemini 3.6/3.7) and **100% Offline Local LLMs (Ollama Llama 3.2, Mistral, Qwen 2.5, DeepSeek R1)** with automatic daemon health detection.
6. **Multi-Session Persistence**: Async relational database persistence (SQLite with aiosqlite or PostgreSQL with asyncpg) storing chat sessions, message histories, timestamps, citation metadata, and generated artifacts.

---

## Technical Stack

- **Backend**: Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (Async), `uv` package manager.
- **Vector Retrieval**: Qdrant vector database with FastEmbed dense (`BAAI/bge-base-en-v1.5`) and sparse (`SPLADE++`) embedding models.
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Lucide React icons.
- **Containerization**: Docker, Docker Compose.

---

## Local Setup and Installation Guide

Follow the step-by-step instructions below to set up and run the entire platform on your local machine.

### 1. Prerequisites and System Requirements

Before starting, ensure you have the following installed on your machine:
- **Python 3.12+**: Tested on Python 3.12.x.
- **`uv` Package Manager**: Fast, deterministic Python package resolver.
  ```bash
  # macOS / Linux
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # Windows
  powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
- **Node.js 18+ and `npm`**: For building and running the React frontend.
  ```bash
  node -v  # Should be v18.0.0 or higher
  npm -v
  ```
- **Docker and Docker Compose** (Recommended): For running the Qdrant vector store and optional containerized deployment.
- **Ollama** (Optional for local offline AI models): Download from [ollama.ai](https://ollama.ai).

---

### 2. Clone the Repository and Configure Environment

```bash
# Clone the repository
git clone https://github.com/Bhaveshupadhyay/yt-assistant.git
cd yt-assistant

# Copy the example environment file
cp .env.example .env
```

Open `.env` and configure your settings if needed. By default, local development uses SQLite (`lenny_assistant.db`) and local Qdrant, requiring no external paid API keys if running with local Ollama.

---

### 3. Start the Vector Database (Qdrant)

The RAG pipeline requires Qdrant for semantic search. You can run Qdrant via Docker with a single command:

```bash
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  -v qdrant_storage:/qdrant/storage \
  qdrant/qdrant:v1.13.4
```

Verify that Qdrant is running by visiting the web dashboard: `http://localhost:6333/dashboard`.

*(Note: If you are using Qdrant Cloud, set `QDRANT_URL` and `QDRANT_API_KEY` in `.env` instead).*

---

### 4. (Optional) Set Up Local LLMs with Ollama

To run offline models without API keys:

1. Start the Ollama background daemon:
   ```bash
   ollama serve
   ```
2. Pull the default local model:
   ```bash
   ollama pull llama3.2
   ```
3. (Optional) Additional supported models:
   ```bash
   ollama pull mistral
   ollama pull qwen2.5
   ```

---

### 5. Backend Setup and Ingestion

The backend uses `uv` for virtual environment management and dependency installation.

```bash
# Navigate to the backend directory
cd backend

# Install all dependencies into virtual environment
uv sync

# Ingest and index podcast transcripts into Qdrant vector store
uv run python -m app.scripts.ingest

# Start the FastAPI development server
uv run uvicorn main:app --reload --port 8000
```

#### Verification:
- Backend Health Check: `http://localhost:8000/health`
- Interactive Swagger API Docs: `http://localhost:8000/docs`
- Alternative ReDoc API Docs: `http://localhost:8000/redoc`

---

### 6. Frontend Setup and Development Server

In a new terminal window:

```bash
# Navigate to the frontend directory
cd frontend

# Install Node dependencies
npm install

# Start the Vite development server
npm run dev
```

#### Access the Application:
- Open your browser to `http://localhost:5173` (or `http://localhost:3000`).
- The frontend automatically proxies API requests to `http://localhost:8000`.

---

### 7. Alternative: One-Command Docker Compose Deployment

If you prefer running everything in containers without manual environment setup:

```bash
# From the project root
docker compose up --build
```

Services started:
- **Frontend Workbench**: `http://localhost:5173`
- **Backend API**: `http://localhost:8000`
- **Qdrant Vector Store**: `http://localhost:6333`

To shut down services:
```bash
docker compose down
```

---

## Running Tests and Code Quality

### Backend Automated Test Suite
Execute the full pytest suite (covering API routes, RAG retrieval, artifact service, and model providers):

```bash
cd backend
uv run pytest
```

### Frontend Build Verification
Verify TypeScript types and produce an optimized production bundle:

```bash
cd frontend
npm run build
```

---

## Environment Variables Reference

Below are the variables supported in `.env` (mirrored in `.env.example`):

| Variable | Default Value | Description |
|---|---|---|
| `APP_NAME` | `"The Lenny Growth Assistant"` | Application name displayed in API docs and UI |
| `APP_VERSION` | `"1.0.0"` | Application version identifier |
| `DEBUG` | `false` | Enable verbose debug output |
| `ENVIRONMENT` | `"development"` | Runtime mode (`development`, `staging`, `production`, `testing`) |
| `DATABASE_URL` | `"sqlite+aiosqlite:///./lenny_assistant.db"` | Async database connection string (SQLite or PostgreSQL) |
| `DATABASE_ECHO` | `false` | Output raw SQL statements to console |
| `QDRANT_URL` | `"http://localhost:6333"` | Qdrant vector database URL |
| `QDRANT_API_KEY` | `""` | Optional API key for Qdrant Cloud |
| `QDRANT_COLLECTION_NAME` | `"lenny_transcripts"` | Qdrant collection name for chunk vectors |
| `OLLAMA_BASE_URL` | `"http://localhost:11434"` | Local Ollama daemon host URL |
| `OLLAMA_MODEL` | `"llama3.2"` | Default local LLM model name |
| `ANTHROPIC_API_KEY` | `""` | Optional API key for Anthropic Claude models |
| `OPENAI_API_KEY` | `""` | Optional API key for OpenAI GPT models |
| `GEMINI_API_KEY` | `""` | Optional API key for Google Gemini models |
| `CORS_ORIGINS` | `["http://localhost:3000","http://127.0.0.1:3000","http://localhost:5173","https://bhaveshupadhyay.github.io","https://lennyai.clientmanger.tech"]` | Allowed CORS origins for frontend client |
| `CORS_ORIGIN_REGEX` | `"https?://.*(clientmanger\\.tech\|github\\.io\|vercel\\.app\|onrender\\.com)"` | Allowed CORS origin regex pattern for preview subdomains |
| `LOG_LEVEL` | `"INFO"` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `LOG_FORMAT` | `"json"` | Log format (`json` or `console`) |

---

## Troubleshooting and FAQ

1. **Ollama daemon not detected (`http://localhost:11434`)**:
   - Ensure Ollama is installed and running: run `ollama serve` in a terminal.
   - If using cloud models, provide an API key (`GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, or `OPENAI_API_KEY`) and toggle the model selector in the UI.
2. **Qdrant connection refused (`http://localhost:6333`)**:
   - Ensure the Qdrant container is active: `docker ps`. If stopped, restart with `docker start qdrant` or run `docker compose up qdrant`.
3. **Database initialization**:
   - SQLite tables are automatically created on first FastAPI server boot. No manual migrations are required for local testing.
4. **Port conflicts**:
   - If port 8000 or 5173 is already in use, you can pass custom ports: `uv run uvicorn main:app --port 8001` or `npm run dev -- --port 5174`.

---

## Project Structure

```text
.
├── .env.example                   # Environment configuration template
├── PRD.md                         # Product Requirements Document
├── README.md                      # Project Overview and Setup Guide
├── architecture.md                # System Architecture and DB Schema
├── design.md                      # UI/UX Design System Specifications
├── Dockerfile                     # Root multi-stage container build definition
├── render.yaml                    # Render Blueprint configuration
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

- **Zero Untrusted Execution**: Generated HTML, CSS, and JavaScript widgets are isolated in an `<iframe>` container with `sandbox="allow-scripts"` (omitting `allow-same-origin` to run in an opaque null origin).
- **Origin Isolation Controls**: Opaque origin strictly blocks script access to parent window DOM, host cookies, local storage, top-level navigation, and form submissions.
- **Typed Schema Validation**: User request parameters and model payloads are strictly typed and validated using Pydantic v2 schemas; untrusted script execution is strictly contained within the sandboxed iframe container.


