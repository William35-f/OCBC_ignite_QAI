# Q AI by Quadrant

**Prototype for OCBC Ignite – Problem Statement 1: "Trusted AI Agents".**
Synthetic data only. Not an OCBC product. No real customer data, documents, rules or limits.

Bank staff increasingly ask AI assistants about internal procedures. A plausible answer that quotes an
outdated rule or skips a required check is worse than no answer. **Q AI** is a checking layer that sits
around such an assistant:

| | |
|---|---|
| **OCBC AI (simulated)** | A basic RAG assistant over a fictional bank's procedures. Deliberately imperfect: its retriever indexes *all* documents, including outdated old versions that a newer version has replaced. |
| **Q AI** | Checks the question **before** OCBC AI answers and the answer **after**. Explains the result, gives Amber answers one retry, and sends untrustworthy answers to a human reviewer. It never edits OCBC AI's answers itself. |

Three roles, switched in the top bar (no login): **Rachel Lim** (Employee, Branch Service Officer),
**Daniel Ng** (Reviewer, Payments Operations), **Priya Nair** (Admin, AI Platform team).

---

## Quick start

Requirements: **Python 3.11+** (built with 3.13), **Node 18+**. Windows, macOS or Linux.

```bash
cd q-ai
npm install          # root helper (concurrently)
npm run setup        # Python venv + backend packages, frontend packages, .env files
npm run dev          # backend http://127.0.0.1:8000 + frontend http://localhost:5173
```

Open **http://localhost:5173**. The first start downloads the embedding model
(sentence-transformers all-MiniLM-L6-v2, about 90 MB). After that everything runs **offline** with the
default mock LLM provider.

| Command | What it does |
|---|---|
| `npm run dev` | Start backend and frontend (Ctrl+C stops both) |
| `npm test` | Backend tests (pytest, 135 tests, about 20 s) |
| `npm run eval` | Run the evaluation (same as `python -m app.eval` in `backend/`) |
| `npm run reset` | Wipe the demo database (stop `npm run dev` first) |
| `npm run build` | Production build of the frontend |
| `npm run dev:api:reload` | Backend only, with auto-reload while you edit code |

### Troubleshooting

| You see | Fix |
|---|---|
| `npm error Missing script: "dev"` | You are in the wrong folder. `cd` into the `q-ai` folder first. |
| "Waiting for the Q AI backend to load…" for a while | Normal on the first start after a reboot: the machine-learning libraries and the embedding model take 1–2 minutes to load. The website starts by itself once the backend prints "Q AI backend ready". |
| "Cannot reach the Q AI backend" in the browser | The backend is not running or still loading. Check the `[api]` lines in the terminal. |
| `address already in use` / port 8000 or 5173 busy | An old `npm run dev` is still running. Close that terminal (or Ctrl+C in it), then start again. |

---

## The workflow

```
1 Prompt ─► 2 Prompt check (Q AI) ─► 3 OCBC AI answers ─► 4 Checks A, B, C in parallel (Q AI) ─► 5 Verdict
             parts, follow-up chips,     RAG over ALL docs,     A rules & timeframes (no LLM)          Green ─► employee
             assumptions, search query   cites (Doc vX, §n)     B sources + counter-evidence          Amber ─► 5b one retry ─► Green? employee : review
                                                                C every question part answered        Red   ─► review queue
                                         6 Evidence view ◄──────────────────────────────────────────── 7 Human review ─► golden set
                                                                                                       8 Dashboard, fixes, retest
```

- **Step 2** – one LLM call returns `parts`, `topic`, `missing_details`, `assumptions`, `search_query`.
  Follow-up chips come only from the matching topic's `required_details`, at most 2, and only when the
  knowledge base clearly covers the question. Each assumption goes through the Step 4B claim checker; a
  contradicted one becomes a correction note shown before the answer. The question itself is never
  replaced: the cleaned query is shown as "Searched for: …".
- **Step 4A (plain Python)** – `citation_exists`, `source_current`, `figures_match` (every amount, %,
  number and date in a cited sentence is in the cited passage), `quotes_match` (quoted text appears word
  for word). A citation covers its own sentence and any uncited sentences just before it.
- **Step 4B** – each sentence is checked against the top 3 passages from **current** documents. Below the
  similarity threshold → "Unable to verify" with no LLM call; everything else is labelled in **one batched
  LLM call** (Supported / Partly supported / Contradicted / Unsupported). Counter-evidence: missing
  exceptions (one LLM call over the "Conditions and exceptions" of the relevant current documents) and
  known conflicts (a lookup in the conflicts table, computed once at load time).
- **Step 4C** – one LLM call: is each question part answered / partly / not answered?
- **Step 5** – rules, no average score. **Red** = any critical flag (contradicted claim, outdated source,
  missing required exception, quote mismatch). **Amber** = no critical flag but at least one warning.
  **Green** = all checks pass.
- **Step 5b** – Amber only, **one** retry: OCBC AI gets its flags plus the correct passages and answers
  again; Q AI re-checks. The original answer is always kept; the employee sees a "What changed" diff.
- **Steps 6–8** – evidence view with highlighted sentences and source passages, Use / Report buttons,
  one review queue (Approve / Correct / Reject with a reason, approved and corrected answers go to the
  golden set), and an admin dashboard with template fix suggestions, **Apply fix** and **Run retest**.

**Design decisions made where the brief left room**

- When two *current* documents conflict, Q AI trusts the one with the later effective date. Citing the
  older side of a known conflict is a warning (Amber); citing the newer side is only an info note.
- Figures the employee typed in a question part (e.g. "S$8,000") are not treated as claims from a source.
  A figure inside an assumption ("Since the limit is S$10,000, …") is still checked.
- A sentence that says the procedure does *not* state something is Supported when no current passage
  states it. A sentence saying "no approved source was found" is always "Unable to verify".
- Retest pass rule: golden-set questions must come out **Green** and contain the golden answer's figures;
  held-out questions must get their expected verdict.

---

## 3-minute demo walkthrough

Start from a clean state: `npm run reset`, then `npm run dev`, open http://localhost:5173 as
**Rachel Lim**. Every question is in the **Demo scenarios** dropdown on the chat page.

1. **Red – Mr Tan (0:00).** Pick *1. Red – Mr Tan's overseas transfer* → **Ask**. Q AI splits the
   question into 2 parts and asks *"Is this payee new or existing?"* → click **New**. Watch the
   "Checking…" steps. OCBC AI answers *S$10,000* from Payments Procedure **v2024**. Verdict:
   **Red: pending review – do not process yet**. Hover the sentences: *S$10,000* is **Contradicted** by
   v2026 §3.1 (S$5,000 for new payees); "Why this verdict" shows the outdated source, the missing
   scam-risk check (§4.2) and part 2 only partly answered. "Use answer" is disabled.
2. **Amber fixed by one retry (0:40).** Pick *2. Amber*. "Transfers usually arrive within 1 business day"
   has no source → Amber → OCBC AI retries once → **Green: corrected answer**. Open **What changed**.
3. **Green (1:00).** Pick *3. Green*. Every sentence Supported → **Use answer** (logged).
4. **Wrong assumption (1:10).** Pick *4*. Before answering, Q AI shows the correction:
   *"Payments Procedure v2026 §3.1 says S$5,000 per day for new payees, not S$10,000."*
5. **No evidence (1:25).** Pick *5*. The claim is **Unable to verify** → Amber → the retry says
   *"No approved source was found…"* → still Amber → **sent for review**.
6. **Review (1:40).** Switch to **Daniel Ng**. Open Mr Tan's question in the queue: original answer,
   flags and evidence side by side. Paste the correction
   *"For a new overseas payee, the limit is S$5,000 per day. Verify the customer's ID and complete the
   scam-risk check before processing."*, reason *"Outdated source, missing exception"* → **Correct**.
   It is saved to the **Golden set** tab. (Rachel's chat now shows the corrected answer.)
7. **Improve (2:15).** Switch to **Priya Nair** → Dashboard. The first suggestion reads
   *"Retire Payments Procedure v2024 from OCBC AI's retriever – … is still being retrieved"*.
   Press **Run retest** → **Failed** (Mr Tan's golden answer is still Red). Press **Apply fix** →
   **Run retest** → **Passed**, suggestion **Done – retest passed**.
8. **Proof (2:45).** Switch back to **Rachel**, ask scenario 1 again with **New** → now **Green**
   (S$5,000 + scam-risk check, from v2026). Scroll Priya's dashboard to the evaluation numbers and the
   Trust Challenge results.

---

## Switching to a real LLM

The mock provider is the default and needs no key. To use **OpenAI** or **Azure OpenAI**, edit
`backend/.env`:

```bash
# OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# or Azure OpenAI (used whenever AZURE_OPENAI_ENDPOINT is set)
LLM_PROVIDER=openai
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT=<deployment name>
AZURE_OPENAI_API_VERSION=2024-06-01
```

Restart the backend. You can also switch provider on the **Settings** page (Priya) and press
**Test provider**. Settings also holds the similarity threshold (default 0.40) and the maximum number of
follow-up questions (0–2).

All prompts are in **`backend/app/core/prompts.py`**. Every structured LLM output is JSON, validated with
Pydantic (`backend/app/schemas/workflow.py`) and retried once if invalid. With a real model, OCBC AI
writes its own answers, so the scripted demo answers no longer apply and results will vary.

---

## Adding a document

1. Create a markdown file in `data/knowledge_base/`, e.g. `cheque-deposits-v2026.md`:

```markdown
---
id: cheque-deposits-v2026
title: Cheque Deposit Procedure
topic: cheque_deposits
version: v2026
effective_date: 2026-05-01
status: current            # current, or superseded = outdated (a newer version replaced it)
superseded_by: null        # id of the newer version that replaced it
owner: Branch Network
required_details:          # follow-up questions Q AI may ask (optional)
  - name: cheque_type
    question: "Is it a local or a foreign cheque?"
    options: ["Local", "Foreign"]
    needed_when: ["clear", "how long"]   # whole words in the question that make it relevant
fields:                    # facts used to detect conflicts between documents
  cheque_daily_limit: "S$50,000"
---
# Cheque Deposit Procedure v2026

## §1 Purpose
This procedure explains how branch staff accept cheque deposits.

## §2 Limits
Cheque deposits up to S$50,000 per day can be accepted at the counter.

## Conditions and exceptions
- [C1] (when: mentions=foreign|overseas; cheque_type=foreign) Foreign cheques need **Payments Operations approval**.
```

2. Restart the backend (`npm run dev`). It re-reads every file, rebuilds the vector store and recomputes
   conflicts (same topic + same field + different value, ignoring outdated documents and old/new
   versions of the same procedure).

Rules: numbered sections use `## §n` or `### §n.m`; every document needs a `## Conditions and exceptions`
section; the **bold** text in a condition is the key phrase an answer must mention; `when:` rules are
`mentions=word|word`, `<detail>=<value>` or `always`, separated by `;`.

---

## Proof it works

- `data/eval/cases.jsonl` – 40 labelled answers, 10 each: correct, missing exception, outdated source,
  no evidence. Q AI checks them directly, bypassing OCBC AI.
- `data/eval/heldout.jsonl` – 10 further questions, used only by **Run retest**.
- `npm run eval` reports missed errors, false flags, accuracy per check (A, B, C), flag recall and Amber
  answers fixed by one retry (full workflow). Results go to `data/eval/results.json` and the dashboard.
- **Trust Challenge** page – 10 answers (5 subtly wrong), Round A text only, Round B with the evidence
  view, shuffled each round; accuracy A vs B is shown on the dashboard.

Current results with the **mock** provider:

| Metric | Result |
|---|---|
| Verdict accuracy | 40 / 40 |
| Missed errors (bad answers shown as Green) | 0 / 30 |
| False flags (correct answers flagged) | 0 / 10 |
| Accuracy per check | A 100% · B 100% · C 92% |
| Expected flags found | 84% |
| Amber answers fixed by one retry | 1 / 3 (the other 2 have no source – correctly sent to review) |

Read these honestly: the mock checker is rule-based and was developed alongside these cases, so the
numbers are optimistic. Known misses: the mock intent check only marks "how / what do I need to" parts
as partly answered, and it labels some no-evidence claims "Unsupported" instead of "Unable to verify"
(the verdict is the same). Re-run the eval with a real LLM for a fairer picture.

---

## Project structure

```
q-ai/
  package.json            npm run setup / dev / test / eval / reset
  scripts/                setup, run-backend, reset helpers
  data/
    knowledge_base/       10 synthetic procedures (markdown + YAML front matter)
    eval/                 cases.jsonl, heldout.jsonl, trust_items.json, results.json
  backend/                FastAPI, SQLAlchemy + SQLite, Chroma, sentence-transformers, Pydantic
    app/
      core/               config, db, runtime settings, prompts.py, llm/ (mock + OpenAI/Azure)
      models/             tables: runs, event log, review items, golden set, fixes, retests, trust results
      schemas/            Pydantic shapes, incl. every LLM output
      routers/            chat, review, admin, kb, settings, trust
      services/
        ingest.py, knowledge_base.py, vector_store.py   load docs, conflicts, Chroma
        prompt_check.py, ocbc_ai.py, workflow.py        Steps 1–3 and orchestration
        checks/rule_check.py, source_check.py, intent_check.py, runner.py   Step 4
        verdict.py, self_correction.py, review.py, improve.py, trust.py      Steps 5–8
      eval.py             python -m app.eval
    tests/                pytest: rules, verdicts, routing, retry limit, conflicts, 5 e2e scenarios, …
  frontend/               React + Vite + TypeScript + Tailwind + React Router + Recharts
    src/theme.ts          all colour tokens (also feeds tailwind.config.ts)
    src/pages/            Chat, ReviewQueue, ReviewDetail, Admin, KnowledgeBase, TrustChallenge, Settings
    src/components/       evidence view, verdict banner, What changed, charts, layout
```

## What is mocked, and known limitations

- **LLM**: the default provider is a deterministic mock. OCBC AI's demo answers are scripted, but they
  depend on what the retriever actually returns (so retiring v2024 really changes the answer). Q AI's
  checks in mock mode are rule-based (figures, keywords, negation, local embeddings for intent).
- **Users**: a role switcher, no authentication. The golden set, reviews and logs live in a local SQLite
  file (`backend/storage/qai.db`).
- **Knowledge base**: loaded at start-up; restart the backend after editing documents. Retiring a
  document only removes it from OCBC AI's retriever; Q AI still reads it.
- The OpenAI / Azure provider is implemented but was not exercised with a real key during development.
- `npm run dev` runs the backend without auto-reload (uvicorn's reloader could hang on Windows); use
  `npm run dev:api:reload` while editing backend code.

---

Prototype for OCBC Ignite. Synthetic data only. Not an OCBC product.
