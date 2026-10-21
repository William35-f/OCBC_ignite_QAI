# Q AI by Quadrant

Prototype for OCBC Ignite, Problem Statement 1: "Trusted AI Agents".
Synthetic data only. Not an OCBC product.

- **OCBC AI (simulated)**: a basic RAG agent over a fictional bank's procedures. Its retriever deliberately indexes superseded documents too.
- **Q AI**: a checking layer that checks the prompt before OCBC AI answers and the answer after, explains the result, retries Amber answers once, and routes untrustworthy answers to a human reviewer.

## Quick start

Requirements: Python 3.13 (or 3.11+), Node 18+.

```bash
npm install        # root helper (concurrently)
npm run setup      # Python venv + backend packages, frontend packages, .env files
npm run dev        # backend on :8000, frontend on http://localhost:5173
npm test           # backend tests
```

The first start downloads the embedding model (all-MiniLM-L6-v2, ~90 MB). After that everything runs offline with the default mock LLM provider.

_Full documentation (switching to a real LLM, adding a document, demo walkthrough) is added in the final build phase._
