# ScholarForge

**Drop a research paper. Get back working code.**

ScholarForge is an autonomous, multi-agent pipeline that reads any ML research paper (PDF), understands its architecture, and generates a working, self-evaluated PyTorch implementation — including a knowledge graph of the model's components and their dependencies.

🔗 **Live demo:** [scholarforge-two.vercel.app](https://scholarforge-two.vercel.app)

---

## What it does

1. **Parses** the paper with Grobid, extracting title, abstract, sections, equations, and references from raw PDF.
2. **Decomposes** the paper into 5 standard ML components (model architecture, loss function, training loop, data preprocessing, evaluation metric) using an LLM (Groq / Llama).
3. **Builds a knowledge graph** mapping how those components depend on each other.
4. **Retrieves similar past implementations** from a vector store (ChromaDB) to ground code generation.
5. **Generates code** for each component, then **self-evaluates** it structurally (AST-based scoring against the retrieved reference) and **retries** automatically if the score is too low.
6. **Pushes the result to GitHub** and surfaces related pretrained models from HuggingFace — both via the real **Model Context Protocol (MCP)**, not direct API calls. An Arxiv search tool is also implemented and exposed over MCP, but isn't currently wired into the automatic pipeline.

The whole flow is orchestrated as a single LangGraph pipeline, exposed over a FastAPI backend with live progress polling, and consumed by a Next.js frontend.

## Architecture

```
PDF Upload
   │
   ▼
Parser Agent (Grobid)
   │
   ▼
Decompose Agent (Groq/Llama) ──► 5 ML components
   │
   ▼
Knowledge Graph Agent ──► dependency graph (NetworkX)
   │
   ▼
Vector Store (ChromaDB) ──► retrieve similar implementations
   │
   ▼
Codegen + Self-Eval Agent ──► generate code, score (AST), retry on low score
   │
   ▼
MCP Tools (real MCP protocol) ──► push to GitHub, find HF models
(Arxiv search also implemented as an MCP tool, available but not auto-called in this flow)
```

## Tech stack

**Backend**
- FastAPI + Uvicorn
- LangGraph for agent orchestration
- Groq API (Llama models) for all LLM calls
- Grobid for PDF parsing
- ChromaDB + sentence-transformers for retrieval
- Real MCP servers/client (Anthropic's MCP SDK) for GitHub, HuggingFace, and Arxiv tool integrations
- Deployed on Hugging Face Spaces (Docker)

**Frontend**
- Next.js 16 + Tailwind CSS v4
- React Flow for the interactive knowledge graph
- Deployed on Vercel

## Why these choices

- **LangGraph over plain function chaining** — explicit state management and node-based structure made it straightforward to add live progress tracking and per-component retry logic.
- **AST-based self-evaluation** — checks structural similarity (classes, functions, control flow) between generated code and a retrieved reference, catching generation failures (e.g. trivial/empty output) without needing to actually execute untrusted generated code.
- **Real MCP protocol** for tool integrations rather than direct API wrapper functions — the GitHub/HuggingFace/Arxiv tools run as an actual MCP server, called over JSON-RPC by an MCP client, the same way Claude Desktop or any MCP-compatible host would call them.
- **Hugging Face Spaces over Render free tier** for backend hosting — the pipeline's memory footprint (ChromaDB + sentence-transformers + concurrent LLM calls) exceeds Render's 512MB free-tier limit; Hugging Face Spaces' free CPU tier offers 16GB.

## Known limitations

- Optimized for ML/deep-learning papers specifically; the 5-component decomposition is hardcoded and will produce a forced, low-quality breakdown if given a non-ML paper.
- The vector store currently has a small seed set of reference implementations per component category, so AST eval scores can be inconsistent — a generated implementation that's structurally different from the single closest reference will score low even if it's reasonable code.
- The public Grobid demo endpoint and free hosting tiers used here have no uptime SLA; expect occasional cold-start delays (~30-60s) after inactivity.

## Running locally

```bash
# Backend
cd backend
pip install -r requirements.txt
docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.0   # Grobid, separate terminal
export GROBID_URL=http://localhost:8070
export GROQ_API_KEY=your_key_here
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

## Project structure

```
backend/
  agents/        # parser, decompose, knowledge graph, codegen, eval agents
  graph/          # LangGraph pipeline definition
  mcp_tools/      # MCP server + client, GitHub/HF/Arxiv tools
  utils/          # AST evaluator
  vector_store/   # ChromaDB wrapper + seed implementations
  main.py         # FastAPI app

frontend/
  app/            # Next.js app router pages
  components/     # uploader, progress tracker, knowledge graph, code viewer
```
