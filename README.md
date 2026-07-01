# AI Customer Support Agent (Multi-Agent)

![CI](https://github.com/Pragatheswar-72/support-agent/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

A multi-agent customer-support system for an e-commerce store. An orchestrator
routes each request to a specialist agent (orders, refunds, payments, FAQ) that
calls real backend tools to resolve it — with guardrails, error handling, and
automatic human-escalation on failure.

## Screenshots

| Order lookup | Guardrail refusal |
|:---:|:---:|
| ![Order lookup](demo/01_order_lookup.png) | ![Guardrail refusal](demo/02_guardrail_refusal.png) |

| Guardrail enforced at the tool level | FAQ answer + session stats |
|:---:|:---:|
| ![Trace showing eligibility check](demo/02b_guardrail_trace_expanded.png) | ![FAQ and sidebar](demo/03_faq_and_sidebar.png) |

The right-hand pair shows the actual mechanism: `check_refund_eligibility`
returns `"eligible": false` for a shipped (not delivered) order, so
`initiate_refund` never even attempts the refund — the rule is enforced in
the tool's code, not just requested in a prompt.

## What it does

- Understands natural-language support requests
- Routes to the right specialist agent (LangGraph orchestration)
- Calls tools that read **and modify** a backend (order status, refunds, payments)
- Remembers context across turns (e.g. "refund it" resolves to the last order discussed)
- Enforces guardrails at the tool level (e.g. refunds only on delivered orders)
- Handles errors with a retry, then escalates to a human with a ticket ID
- Shows a live agent trace: which agent handled the request and which tools it called
- Tracks token usage per session and caches repeated FAQ answers to save quota
- Exposes the same orchestrator over a **FastAPI** REST endpoint, not just the chat UI
- Ships with a **routing evaluation harness** that measures LLM classification accuracy on a curated dataset, separate from unit tests

## Tech

LangGraph multi-agent orchestration · Gemini tool-calling (with Groq fallback)
· SQLite backend (SQLAlchemy) · Streamlit · FastAPI · pytest

## Architecture

```
              Streamlit UI (app.py)   FastAPI (api.py)
                        |                   |
                        +--------+----------+
                                 v
                   +--------------------+
                   |   ORCHESTRATOR     |  <- classifies intent, routes,
                   |   (LangGraph)      |     holds conversation memory
                   +---------+----------+
        +----------+---------+----------+-----------+
        v          v         v          v            v
   +--------+ +--------+ +--------+ +--------+  (no match / fails)
   | ORDER  | | REFUND | |PAYMENT | |  FAQ   |        |
   | agent  | | agent  | | agent  | | agent  |        v
   +---+----+ +---+----+ +---+----+ +---+----+   +----------+
       | tools    | tools    | tools    |        | ESCALATE |
       v          v          v          v        | to human |
   +---------------------------------------+     +----------+
   |   SQLite backend                      |
   |   orders / payments / refunds tables  |
   +---------------------------------------+
```

## How it works

1. The orchestrator (a LangGraph graph) classifies the message into ORDER,
   REFUND, PAYMENT, FAQ, or ESCALATE.
2. The matching specialist agent decides which tool(s) to call and with what
   arguments (Gemini/Groq tool-calling), then turns the tool result into a
   natural-language reply.
3. Tools read from and write to a SQLite database — refunds and payments are
   real state changes, not simulated text.
4. Guardrails are enforced in the tools themselves (not just the prompt): for
   example `initiate_refund` always re-checks eligibility before acting, so
   an LLM can't talk its way around the rule.
5. If the whole pipeline fails (e.g. an API outage or rate limit), it retries
   once, then calls `escalate_to_human`, which returns a ticket ID instead of
   crashing.
6. Conversation memory tracks the last order discussed, so follow-up messages
   like "refund it" resolve correctly across agent switches.

## Run locally

1. `python -m venv venv` and activate it
   (`.\venv\Scripts\Activate.ps1` on Windows, `source venv/bin/activate` on macOS/Linux).
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and add your `GEMINI_API_KEY`
   (free key: https://aistudio.google.com/app/apikey). Optionally add
   `GROQ_API_KEY` (free key: https://console.groq.com) as a fallback for when
   the Gemini free tier's daily quota is exhausted.
4. `python -m src.backend.seed` — creates and seeds the SQLite database.
5. `streamlit run app.py`

## Run the API (FastAPI)

```
uvicorn api:app --reload
```

Then open interactive docs at http://localhost:8000/docs. Example flow:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "where is order 1001?"}'

# reuse the returned session_id to keep conversation memory across turns
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "refund it, it arrived broken", "session_id": "<id from above>"}'
```

Every request is logged as structured JSON (method, path, status, latency).
The Streamlit UI and the API both call the same `src/orchestrator.py`, so the
agent logic is written once and consumed by either a human (UI) or a machine
(API) — exactly like the Resume Analyser project.

## Tests

```
pytest
```

35 tests covering: every tool against a seeded in-memory database (including
the refund-eligibility guardrail), orchestrator routing for all five paths
(mocked LLM, no API key needed), conversation memory, retry/escalation
behavior on a forced failure, and the FastAPI endpoints (session handling,
validation, mocked orchestrator).

## Evaluation

A routing evaluation harness measures whether the router LLM classifies
realistic (and deliberately tricky) customer messages correctly — this is
different from the unit tests, which only check the graph wiring with a
mocked LLM:

```
python eval/run_eval.py --dry-run   # validates the dataset, no API calls
python eval/run_eval.py             # calls the real LLM, reports accuracy
```

On the bundled 21-scenario dataset (`eval/eval_dataset.json`) this currently
scores 100% routing accuracy.

## Docker

```
docker build -t support-agent .
docker run -p 8501:8501 -e GEMINI_API_KEY=your_key support-agent
```

## Deploy (Streamlit Community Cloud)

1. Push this repo to GitHub.
2. On https://share.streamlit.io, create an app from the repo, main file `app.py`.
3. In the app's **Secrets**, add:
   ```
   GEMINI_API_KEY = "your_key_here"
   GROQ_API_KEY = "your_key_here"   # optional fallback
   ```
   Never commit the real key — `.env` is git-ignored.
4. That's it — the SQLite file isn't committed to the repo, but `src/tools.py`
   auto-seeds the database on first import if it's empty, so a fresh
   deployment works with no extra startup step.

## Cost

Runs on free-tier infrastructure: Gemini's free tier for the primary LLM,
with an optional Groq free-tier fallback and FAQ-answer caching to reduce
repeat calls. Realistic cost: **$0**.

## Configuration

- `GEMINI_API_KEY` — required.
- `GEMINI_API_KEYS` — optional comma-separated pool of Gemini keys (only
  useful if they're under separate Google Cloud projects with independent
  quota — keys under the same project share one quota bucket).
- `GEMINI_MODEL` — optional, defaults to `gemini-2.5-flash`.
- `GROQ_API_KEY` / `GROQ_MODEL` — optional fallback provider, defaults to
  `llama-3.3-70b-versatile`. Used automatically once all Gemini keys are
  exhausted.
