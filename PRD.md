# Product Requirements Document (PRD)

## Project: The Lenny Growth Assistant
**Role:** Forward Deployed Engineer (FDE)  
**Target Delivery:** High-Growth Product and Growth Teams  
**Version:** 1.0.0  

---

## 1. Executive Summary and Problem Space

### 1.1 Problem Statement
Product Managers, Growth Leads, and Founders frequently need battle-tested tactical guidance on high-stakes challenges such as pricing and packaging strategy, Product-Led Growth (PLG) onboarding, retention loop diagnostics, and organizational scaling. While *Lenny's Podcast & Newsletter* contains over 400 hours of gold-standard insights from top operators (Airbnb, Figma, Stripe, Uber, Amplitude, Snowflake), this knowledge remains locked in unstructured audio and long transcripts.

**The Current Pain Points:**
- **Time Sink:** Digging through transcripts or listening to multi-hour episodes takes hours of manual work.
- **Generic AI Hallucinations:** Public LLMs (e.g., standard ChatGPT) produce generic corporate advice rather than nuanced, battle-tested operator frameworks.
- **High Formatting Friction:** Converting transcript insights into executive memos, checklists, or interactive tools requires significant manual synthesis.
- **Data Privacy and Offline Needs:** Teams often need the option to evaluate and synthesize proprietary startup data without sending queries to third-party public clouds.

### 1.2 The Solution
**The Lenny Growth Assistant** is an internal AI conversational assistant and live artifact workbench that:
1. Grounds answers strictly in Lenny's podcast transcript corpus with verifiable verbatim citations and guest attribution as a hard runtime invariant (system explicitly declines to answer if no relevant transcript context is retrieved).
2. Formats strategic insights into structured, viral **"Ship 30 for 30"** atomic essays (~1,250 words).
3. Renders interactive, sandboxed **Markdown and HTML/CSS/JS Artifacts** (calculators, checklists, frameworks) side-by-side with chat.
4. Toggles seamlessly between **Enterprise Cloud LLMs (Anthropic Claude, OpenAI, Google Gemini)** and **100% Offline Local LLMs (Ollama)**.
5. Persists multi-session conversation history and generated artifacts across sessions using an async database backend.

---

## 2. Target Users and Personas

| Persona | Primary Job to be Done (JTBD) | Pain Solved by Assistant |
|---|---|---|
| **Growth Lead / PM** | Formulate growth loops, retention strategies, and pricing experiments. | Synthesizes tactical frameworks across top growth operators (Elena Verna, Brian Balfour, Casey Winters) in seconds. |
| **Founder / Operator** | Draft strategic memos, board slides, and public thought leadership. | Converts transcript wisdom into ~1,250-word structured essays using the "Ship 30 for 30" framework. |
| **Product Designer / Engineer** | Implement quick checklists, calculators, or landing page mockups. | Generates live, interactive HTML/CSS/JS artifacts rendered in a safe sandbox viewer. |

---

## 3. Key Assumptions and Scope Boundaries

### 3.1 Assumptions Made
1. **Curated High-Impact Corpus:** Ingesting 10 to 25 cornerstone episodes (e.g., PLG, Pricing, Retention, Hiring) provides sufficient depth for evaluation and demo queries.
2. **Deterministic Attribution:** Episode titles, guest roles, and timestamps provide full attribution without requiring compute-heavy audio speaker diarization.
3. **Local and Cloud Hardware Feasibility:** Evaluators have Ollama installed locally or can supply an Anthropic, OpenAI, or Gemini API key for cloud model execution.

### 3.2 In-Scope vs. Out-of-Scope

| In-Scope | Out-of-Scope |
|---|---|
| Strict RAG retrieval on Lenny transcripts (Qdrant + FastEmbed) | Real-time live audio voice transcription |
| Verifiable episode, guest, and timestamp citation badges | Multi-tenant organization billing and Stripe integration |
| Multi-provider LLM toggle (Claude, OpenAI, Gemini, Local Ollama) | Direct video streaming/playback embed |
| Dedicated "Ship 30 for 30" Essay generator tool | Full sub-agent swarm hierarchies |
| Sandboxed side-by-side Artifact Viewer (Preview + Code tabs) | Automated web scraping of external paywalled posts |
| Persistent multi-session chat and artifact storage (SQLite / PostgreSQL) | Native mobile application packaging |
| Single-command Docker Compose deployment | Multi-lingual speech translation |

---

## 4. Measurable Success Metrics

1. **Groundedness and Accuracy:** Hard runtime invariant of zero ungrounded hallucinations (the assistant explicitly declines to answer when data is absent in retrieved transcripts); empirical acceptance benchmark threshold of >= 95% verifiable citation accuracy against gold-standard evaluation suites.
2. **Query Latency Targets:**
   - Vector Search Retrieval: < 150 ms.
   - First Token Time (Cloud LLMs): < 1.0 s.
   - First Token Time (Local Ollama): < 2.5 s.
3. **Synthesis Speedup:** Time required to produce a publication-grade strategy memo reduced from 3 hours to < 45 seconds.
4. **Deployment Reliability:** 100% pass rate on single-command startup (`docker compose up --build`) on clean evaluator environments.

---

## 5. Core Feature Specifications and System Flows

### 5.1 System Data Flow

```text
[User Prompts] ---> [Intent Router] ---> [RAG Vector Search] ---> [Context Assembly]
                                                                        |
                         +----------------------------------------------+-------------------------+
                         |                                                                        |
                         v                                                                        v
              [Standard Q&A Mode]                                                         [Specialized Skills]
          - Grounded answer + Badges                                                  - "Ship 30 for 30" Essay (~1,250w)
          - Zero-hallucination fallback                                               - HTML/CSS Artifact in Sandbox
```

### 5.2 Grounded Q&A and Citation Flow
- **Input Processing**: The user submits a natural language question (e.g., *"How do I fix customer churn after onboarding?"*).
- **Hybrid Retrieval**: The backend embeds the query using FastEmbed dense (`BAAI/bge-base-en-v1.5`) and sparse (`SPLADE++`) encoders, querying Qdrant for top 3 to 5 chunks.
- **Prompt Construction**: Relevant chunks with metadata (Guest name, Episode title, YouTube timestamp URL) are injected into the system prompt alongside strict attribution rules.
- **Interactive Badges**: The frontend renders citation badges that expand on click to show transcript source snippets.

### 5.3 "Ship 30 for 30" Essay Skill
- **Activation**: Triggered via user prompt intent or UI action button.
- **Structural Blueprint**:
  - Word count: ~1,250 words.
  - Sentence cadence: 1-3-1 pacing for readability.
  - Hook: Contrarian truth or high-stakes problem statement.
  - Visual hierarchy: Bolded first 2 to 4 words of key bullet points.
  - Closing: Actionable 3-step execution checklist.

### 5.4 In-App Sandboxed Artifact Viewer
- **Separation of Concerns**: Response payloads cleanly separate conversational commentary from code/artifact blocks.
- **Split-Screen Workbench**: Right-hand drawer slides open displaying **Preview** and **Code** tabs.
- **Security Sandboxing**: HTML/JS artifacts execute inside an `<iframe sandbox="allow-scripts">`. Because `allow-same-origin` is omitted, the document runs with an opaque null origin, preventing parent DOM access, cookie access, local storage access, top-level navigation, and form submissions.

### 5.5 Multi-Provider Model Architecture
- **Supported Providers**: Anthropic (Claude 3.5 Sonnet, Claude 3.7 Sonnet), OpenAI (GPT-4o, GPT-4o-mini), Google Gemini (Gemini 3.6 Flash, Gemini 3.6 Flash Lite, Gemini 3.7 Pro), and Local Ollama (Llama 3.2, Mistral, Qwen 2.5, DeepSeek R1).
- **Offline Daemon Detection**: System probes `http://localhost:11434` health. If offline, the UI provides a non-blocking alert with a one-click action to switch to an available Cloud provider.

---

## 6. Risks and Mitigation Plan

| Risk | Impact | Mitigation Strategy |
|---|---|---|
| **Hallucination on Niche Queries** | High | System prompt strictly instructs model to declare lack of evidence if relevance score falls below threshold. |
| **Local Ollama Unavailable** | Medium | Backend detects connection timeout on port 11434, alerts UI, and provides one-click manual fallback to available Cloud providers. |
| **Malicious HTML Artifacts (XSS)** | High | Sandboxed `<iframe>` with `sandbox="allow-scripts"` (opaque origin) preventing parent DOM access, cookie theft, and local storage access. |
| **Context Window Overflow** | Low | Semantic chunking with top-k token capping (max 3,000 context tokens injected per query). |
| **Database Lock Contention** | Low | Async connection pooling with SQLAlchemy 2.0 and WAL mode enabled for SQLite / connection pool for PostgreSQL. |


