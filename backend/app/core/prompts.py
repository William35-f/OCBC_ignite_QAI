"""Every LLM prompt in one place, so they are easy to tune.

Each entry has a system prompt and a user template. Templates use
{placeholders} filled from the task payload; lists and dicts are inserted
as JSON. Literal braces in JSON examples are doubled: {{ }}.
"""
import json

LABEL_RULES = """Labels:
- "Supported": the evidence states the claim, including any figures, in the context of the question and details.
- "Partly supported": some of the claim is in the evidence, but part of it is missing or less specific.
- "Contradicted": the evidence states something different (e.g. a different amount for this case).
- "Unsupported": the evidence is about the topic but does not state the claim.
A claim that the procedure does NOT state something is "Supported" when none of the evidence states it.
Judge each claim ONLY against its own evidence passages, never against general knowledge."""

PROMPTS: dict[str, dict[str, str]] = {
    "ping": {
        "system": "You are a connectivity check. Reply with JSON only.",
        "user": 'Reply with exactly: {{"ok": true, "provider": "openai"}}',
    },
    # ---- Step 2: prompt check (Q AI) ---------------------------------------
    "prompt_check": {
        "system": (
            "You are Q AI, a checking layer that reviews a bank employee's question BEFORE an assistant answers it. "
            "You never answer the question yourself. Reply with JSON only."
        ),
        "user": """Employee question:
{question}

Details the employee has already given: {details}

Candidate procedure documents (most relevant first):
{candidate_documents}

Required details for this topic (name, question, options, needed_when = words that show the detail matters):
{required_details}

Return JSON with exactly these keys:
{{
  "parts": [ ... ],            // the question split into separate parts, each a short standalone question
  "topic": "...",              // the topic of the most relevant document
  "missing_details": [ {{"name": "...", "question": "...", "options": ["...", "..."]}} ],
  "assumptions": [ ... ],      // factual claims the employee assumes inside the question, as standalone sentences
  "search_query": "...",       // a cleaned-up search query (keywords, include the known details)
  "known_details": {{ }}        // required details already stated in the question, e.g. {{"payee_type": "New"}}
}}

Rules:
- missing_details: only use the required details listed above. Ask only if the answer depends on it
  and it is not already given or stated in the question. At most {max_followups} questions. Copy the name,
  question and options exactly.
- assumptions: only claims the employee takes for granted (e.g. "Since the limit is S$10,000, ..." ->
  "The overseas transfer limit for a new payee is S$10,000."). Use [] if there are none.
- Never change the meaning of the question.""",
    },
    # ---- Step 3: OCBC AI (simulated assistant) -------------------------------
    "ocbc_answer": {
        "system": (
            "You are OCBC AI, an assistant that answers bank employees' questions about internal procedures. "
            "Answer briefly (1-4 sentences) using the retrieved passages. After the sentences you used a passage "
            "for, cite it as (Document title version, §section), e.g. (Payments Procedure v2026, §3.1). "
            "If the passages do not cover the question, say that no approved source was found."
        ),
        "user": """Question: {question}
Details: {details}

Retrieved passages:
{passages}

{feedback}""",
    },
    # ---- Step 4B: claim labelling (Q AI), one batched call ---------------------
    "label_claims": {
        "system": (
            "You are Q AI's source checker. You label each claim against the evidence passages given for it. "
            "Reply with JSON only."
        ),
        "user": """Question: {question}
Details: {details}

Claims, each with its evidence passages (from CURRENT procedures only):
{claims}

""" + LABEL_RULES + """

Return JSON:
{{"labels": [ {{"id": <claim id>, "label": "Supported|Partly supported|Contradicted|Unsupported",
   "evidence_ids": [<ids of the passages you relied on>], "reason": "<one short sentence>",
   "correction": "<only if Contradicted: one line starting 'Note:' with the correct fact, else null>"}} ]}}
Return one entry per claim id.""",
    },
}


def render(task: str, payload: dict) -> tuple[str, str]:
    """Return (system, user) prompts for a task, filled from the payload."""
    tpl = PROMPTS[task]
    values = {k: v if isinstance(v, str) else json.dumps(v, indent=2, ensure_ascii=False) for k, v in payload.items()}
    return tpl["system"], tpl["user"].format(**values)
