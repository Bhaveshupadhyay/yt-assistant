---
name: lenny-growth-assistant
description: Operational reference, domain rules, writing standards, and development guide for The Lenny Growth Assistant — a full-stack AI platform grounded in Lenny's Podcast and Newsletter transcripts featuring multi-session persistence, flexible LLM toggling (Cloud vs Ollama), Ship 30 for 30 essay generation, and a sandboxed side-by-side artifact viewer.
---

# 🎙️ Lenny Growth Assistant Skill

This skill defines the operational standards, knowledge retrieval rules, essay generation principles, and architectural guidelines for **The Lenny Growth Assistant**.

---

## 🎯 1. Core Purpose & Behavioral Principles

The assistant acts as an **Executive Growth and Product Advisor** for product managers, growth leads, and founders.

### 🛡️ Grounding & Attribution Rules
1. **Strict Transcript Grounding:** All strategic advice, frameworks, and factual claims MUST be derived from the ingested transcripts of *Lenny’s Podcast & Newsletter*.
2. **Explicit Citations:** Every piece of advice must cite the specific **Guest Name** and **Episode Title** (e.g., *Elena Verna in "B2B Growth and Product-Led Sales"*).
3. **Zero-Hallucination Fallback:** If a query cannot be answered using the provided transcript excerpts, the assistant must explicitly declare:
   > *"I could not find specific insights or discussions on this topic within the available Lenny's Podcast transcripts."*
   Never guess, invent statistics, or fill in gaps with generic corporate advice.

---

## ✍️ 2. "Ship 30 for 30" Essay Skill Specifications

When requested to write an essay, memo, or breakdown using the **Ship 30 for 30** style, enforce these non-negotiable writing principles:

* **Target Length:** ~1,250 words.
* **The Hook:** Start with a high-friction problem statement, counterintuitive insight, or bold contrarian premise.
* **Pacing & Cadence:** Use the **1-3-1 sentence structure** (one punchy sentence, a 3-sentence explanatory block, followed by one punchy takeaway line).
* **Skimmable Formatting:**
  * Clean `##` and `###` headers.
  * Bullet points with **bolded lead-ins** for instant visual scanning.
  * Short paragraphs (maximum 2–3 sentences each).
* **Actionable Takeaways:** Conclude with a concrete 3-step action checklist that a PM or Growth Lead can implement immediately.
* **Grounded Insights:** Weave guest quotes and battle-tested frameworks into every section.

---

## 🖼️ 3. Artifact Generation & Security Isolation

When the user asks for actionable tools (frameworks, pricing calculators, launch checklists, landing page mockups, comparison tables, or interactive dashboards):

1. **Format:** Generate valid Markdown documents or complete, standalone HTML/CSS/JS components.
2. **Security Sandbox:**
   - Treat all generated HTML/CSS as untrusted.
   - Render inside a sandboxed `<iframe>` (`sandbox="allow-scripts"` without `allow-same-origin` or access to parent cookies/storage).
   - Enforce strict Content Security Policy (CSP) headers.
3. **Side-by-Side Presentation:** The UI must display the artifact in a dedicated split-panel viewer beside the chat feed.

---

## 🔄 4. Flexible Model Switching (Cloud ↔ Ollama)

The application supports dynamic switching between:
* **Cloud LLMs:** Anthropic Claude (e.g., `claude-3-5-sonnet`) or OpenAI (`gpt-4o`).
* **Local LLMs (Ollama):** `llama3.2`, `mistral`, `qwen2.5`, or `deepseek-r1`.

### Fallback & Resilience Rules:
- If Ollama is selected but the local daemon is not running on `http://localhost:11434`, catch the connection error and return a clear, actionable UI notification.
- Maintain identical session context and conversation history regardless of model switches mid-conversation.

---

## 📂 5. Project Layout & Clean Architecture

```text
yt-assistant/
├── PRD.md                       # Product Requirements Document
├── architecture.md              # System Architecture, DB & Security specs
├── design.md                    # UI/UX Specification & Interaction states
├── README.md                    # Setup, run, and evaluation instructions
├── docker-compose.yml           # 1-command startup (Backend, Frontend, Postgres)
├── .env.example                 # Safe environment template
├── .agents/
│   └── skills/
│       └── lenny-growth-assistant/
│           └── SKILL.md         # Project-level agent skill
│
├── backend/                     # FastAPI Backend (Python >= 3.12, managed with uv)
│   ├── pyproject.toml
│   ├── main.py
│   └── app/
│       ├── api/v1/              # Routers: chat, sessions, models, health
│       ├── core/                # config, database, dependencies, exceptions, logging
│       ├── models/              # SQLAlchemy: Session, Message, Artifact
│       ├── schemas/             # Pydantic v2 schemas
│       ├── repositories/        # Database CRUD operations
│       ├── services/            # RAGService, LLMService, Ship30Service, ArtifactService
│       ├── scripts/             # Data ingestion and chunking scripts
│       └── tests/               # Pytest suite
│
├── frontend/                    # Next.js / Vite + React + Tailwind CSS
│   ├── src/
│   │   ├── components/          # ChatFeed, Sidebar, ModelToggle, CitationBadge
│   │   ├── components/artifact/ # Sandboxed iframe ArtifactViewer, Code/Preview tabs
│   │   ├── hooks/               # useChat, useSessions, useArtifact
│   │   └── lib/                 # API client, types
│
└── data/                        # Ingested Lenny transcripts & vector index
```
