# The Lenny Growth Assistant - Frontend

An enterprise AI productivity workbench built with React, TypeScript, Vite, and Tailwind CSS. Grounded strictly in *Lenny's Podcast & Newsletter* transcripts.

## Features
- **Split-Screen Workbench**: Multi-session sidebar + streaming conversational feed + sandboxed side-by-side artifact viewer.
- **Strict Grounding**: Real-time SSE token streaming with verifiable citation pills linking to podcast excerpts and YouTube timestamps.
- **Dynamic Model Switching**: Cloud LLMs (Claude 3.5 Sonnet, GPT-4o, Gemini) and Local Ollama with offline daemon detection.
- **Isolated Artifact Sandbox**: Sandboxed `<iframe>` rendering for generated HTML/JS widgets, dashboards, and checklists with strict CSP.
- **Ship 30 for 30 Essay Mode**: Dedicated tool toggle to generate ~1,250-word atomic essays with 1-3-1 pacing.

## Available Scripts

### Development
```bash
npm install
npm run dev
```
Starts the local development server at `http://localhost:5173` with automatic API proxying to `http://localhost:8000`.

### Production Build
```bash
npm run build
npm run preview
```
Typechecks and compiles production static assets to `dist/`.
