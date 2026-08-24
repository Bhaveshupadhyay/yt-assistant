# The Lenny Growth Assistant
> **Forward Deployed Engineer (FDE) Take-Home Assignment Submission**  
> An internal, conversational AI workbench grounded in *Lenny’s Podcast & Newsletter* transcripts, featuring multi-session persistence, flexible LLM toggling (Cloud ↔ Ollama), Ship 30 for 30 essay generation, and a sandboxed side-by-side artifact viewer.

---

## 📚 Table of Deliverables & Documentation

| Document | Description |
|---|---|
| 📄 [**`PRD.md`**](./PRD.md) | **Product Requirements Document**: User personas, problem statement, success metrics, assumptions, in/out-of-scope boundaries, and risk mitigation. |
| 🏗️ [**`architecture.md`**](./architecture.md) | **System Architecture**: PostgreSQL schema, FastAPI Clean Architecture, RAG chunking & retrieval, Model toggle (Claude/Ollama), and iframe sandbox security. |
| 🎨 [**`design.md`**](./design.md) | **UI/UX Design Specification**: Split-screen workbench layout, interaction states (streaming, citations, artifacts), accessibility, and design tokens. |
| 🤖 [**Agent Skill (`SKILL.md`)**](file:///Users/bhaveshupadhyay/.agents/skills/lenny-growth-assistant/SKILL.md) | **AI Agent Skill**: Operational domain rules, citation requirements, and Ship 30 for 30 writing standards. |

---

## 🚀 Core Features

1. **Strict Transcript Grounding (RAG)**: Answers product & growth questions using *Lenny's Podcast* transcripts with verifiable guest attribution (e.g., Elena Verna, Brian Balfour, Shreyas Doshi). Includes a strict zero-hallucination fallback.
2. **Dedicated "Ship 30 for 30" Essay Engine**: Automatically synthesizes transcript wisdom into ~1,250-word atomic essays featuring magnetic hooks, 1-3-1 pacing, visual bolding, and actionable checklists.
3. **Claude-Style In-App Artifact Viewer**: Renders interactive HTML/CSS widgets, calculators, and Markdown documents in a side-by-side split screen.
4. **Untrusted HTML Security Sandbox**: Isolated `<iframe>` execution with strict Content Security Policy (`connect-src 'none'`) preventing parent DOM access or cookie leakage.
5. **Flexible Model Toggle**: Run against enterprise Cloud LLMs (Anthropic Claude / OpenAI) or **100% offline Local LLMs (Ollama)** with automatic fallback.
6. **Multi-Session Persistence**: PostgreSQL database storing chat sessions, message history, timestamps, and generated artifacts.

---

## 🛠️ Quickstart & Development

### 1. One-Command Docker Setup
```bash
docker compose up --build
```

### 2. Local Development (Backend with `uv`)
```bash
cd backend
uv sync
uv run python -m app.scripts.ingest
uv run uvicorn main:app --reload --port 8000
```

### 3. Local Development (Frontend)
```bash
cd frontend
npm install
npm run dev
```

### 4. Running Tests
```bash
cd backend
uv run pytest
```
