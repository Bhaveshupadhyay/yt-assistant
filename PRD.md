# Product Requirements Document (PRD)
## Project: The Lenny Growth Assistant
**Role:** Forward Deployed Engineer (FDE)  
**Target Delivery:** High-Growth Product & Growth Teams  
**Version:** 1.0.0  

---

## 1. Executive Summary & Discovery Brief

### 1.1 Problem Statement
Product Managers, Growth Leads, and Founders often need battle-tested tactical guidance on urgent challenges (e.g., pricing strategy, PLG onboarding, retention cliffs, org hiring). While *Lenny’s Podcast & Newsletter* contains over 400+ hours of gold-standard insights from top operators (Airbnb, Figma, Stripe, Uber, Amplitude), this knowledge is locked in unstructured, long-form audio and transcripts.

**The Current Pain:**
- **Time Sink:** Digging through transcripts or listening to multi-hour episodes takes hours.
- **Generic AI Hallucinations:** Public LLMs (ChatGPT) produce generic corporate platitudes rather than nuanced operator frameworks.
- **High Formatting Friction:** Turning transcript insights into executive memos or interactive tools requires extensive manual work.
- **Data Privacy Risks:** Teams cannot paste proprietary startup data or metrics into unverified public cloud tools.

### 1.2 The Solution
**The Lenny Growth Assistant** is an internal AI conversational assistant and live artifact workbench that:
1. Ground answers 100% in Lenny's podcast transcript corpus with verbatim citations and guest attribution.
2. Formats strategic insights into viral, atomic **"Ship 30 for 30"** essays (~1,250 words).
3. Renders interactive, sandboxed **Markdown and HTML/CSS Artifacts** (calculators, checklists, frameworks) side-by-side with chat.
4. Toggles seamlessly between **Enterprise Cloud LLMs (Anthropic Claude)** and **100% Offline Local LLMs (Ollama)**.

---

## 2. Target Users & Personas

| Persona | Primary Job to be Done (JTBD) | Pain Solved by Assistant |
|---|---|---|
| **Growth Lead / PM** | Formulate growth loops, retention strategies, and pricing experiments. | Synthesizes tactical frameworks across 10+ growth guests (Elena Verna, Brian Balfour, Casey Winters) in seconds. |
| **Founder / Operator** | Draft strategic memos, board slides, and public thought leadership. | Converts transcript wisdom into ~1,250-word structured essays using the "Ship 30 for 30" skill. |
| **Product Designer / Dev** | Implement quick checklists, calculators, or landing page mockups. | Generates live, interactive HTML/CSS artifacts in a sandboxed viewer. |

---

## 3. Key Assumptions & Scope Boundaries

### 3.1 Assumptions Made
1. **Curated High-Impact Corpus:** Ingesting 10–25 cornerstone episodes (e.g., PLG, Pricing, Retention, Hiring) provides sufficient depth for evaluation and demo queries.
2. **Deterministic Attribution:** Episode titles, guest roles, and timestamps provide full attribution without requiring compute-heavy audio speaker diarization.
3. **Local Machine Feasibility:** Evaluators have Ollama installed or can test against an OpenAI/Anthropic API key fallback.

### 3.2 In-Scope vs. Out-of-Scope

```
┌───────────────────────────────────────────────┬───────────────────────────────────────────────┐
│                   IN-SCOPE                    │                 OUT-OF-SCOPE                  │
├───────────────────────────────────────────────┼───────────────────────────────────────────────┤
│ • Strict RAG retrieval on Lenny transcripts   │ • Real-time live audio voice transcription    │
│ • Episode & Guest citation badges             │ • Multi-tenant organization billing/Stripe    │
│ • Local Ollama + Cloud Claude/OpenAI toggle   │ • Direct video streaming/playback embed       │
│ • "Ship 30 for 30" Essay generator tool       │ • Full sub-agent swarm hierarchies           │
│ • Sandboxed side-by-side Artifact Viewer      │ • Automated web scraping of paywalled posts   │
│ • PostgreSQL multi-session chat persistence   │                                               │
│ • Docker Compose 1-command startup            │                                               │
└───────────────────────────────────────────────┴───────────────────────────────────────────────┘
```

---

## 4. Measurable Success Metrics

1. **Groundedness & Accuracy:** ≥ 95% of factual claims cite specific guest names and episodes; 0% ungrounded hallucinations (assistant admits when data is absent).
2. **Query Latency:**
   - Vector Search Retrieval: < 150 ms.
   - First Token Time (Cloud): < 1.0 s.
   - First Token Time (Local Ollama): < 2.5 s.
3. **Synthesis Speedup:** Time to produce a publication-grade strategy memo reduced from 3 hours to < 45 seconds.
4. **Operability:** 100% pass rate on 1-command startup (`docker compose up`) on clean evaluator machines.

---

## 5. Core Feature Specifications & User Flows

```
[User Prompts] ──► [Intent Router] ──► [RAG Vector Search] ──► [Context Assembly]
                                                                        │
                         ┌──────────────────────────────────────────────┴────────────────────────┐
                         ▼                                                                       ▼
             [Standard Q&A Mode]                                                         [Specialized Skills]
         - Grounded answer + Badges                                                  - "Ship 30 for 30" Essay (~1,250w)
         - Zero-hallucination fallback                                               - HTML/CSS Artifact in Sandbox
```

### 5.1 Grounded Q&A & Citation Flow
- User submits a question (e.g., *"How do I fix customer churn after onboarding?"*).
- System embeds query, retrieves top 3–5 chunks with metadata (Guest, Episode, URL).
- Prompt injects strict citation rules.
- Assistant renders response with interactive citation pills that expand to show the source snippet.

### 5.2 "Ship 30 for 30" Essay Skill
- Triggered by prompt or UI action button.
- Structures output into ~1,250 words following the 1-3-1 sentence structure, magnetic hook, bolded bullet points, and an actionable 3-step closing checklist.

### 5.3 In-App Sandboxed Artifact Viewer
- When code or formatted tools are requested, the response separates chat commentary from the artifact payload.
- Right-hand drawer slides open with **Preview** and **Code** tabs.
- HTML is rendered inside an `<iframe sandbox="allow-scripts">` with strict CSP (no parent window access or cookie leakage).

---

## 6. Risks & Mitigation Plan

| Risk | Impact | Mitigation Strategy |
|---|---|---|
| **Hallucination on Niche Queries** | High | System prompt strictly instructs model to declare lack of evidence if relevance score is below threshold. |
| **Local Ollama Unavailable** | Medium | Backend detects connection timeout on port 11434, alerts UI, and offers automatic fallback to Cloud provider. |
| **Malicious HTML Artifacts (XSS)** | High | Sandboxed `<iframe>` with restrictive CSP blocking parent DOM access, cookie theft, and external scripts. |
| **Context Window Overflow** | Low | Semantic chunking with top-k token capping (max 3,000 context tokens injected per query). |
