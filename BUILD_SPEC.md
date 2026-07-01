# Project 2 — Customer Support Agent: Full Build Spec
> A complete specification to hand to **Claude Code**. Covers what to build, the tech stack, multi-agent architecture, the fake backend, tools, error handling, deployment, README, and interview prep.
> **Budget: $0.** Free LLM tier + free hosting.
> **The one rule that makes this a real project:** the agent must *take actions* against a backend, not just chat. Actions over answers.
---
## 1. What this project is (one paragraph)
A **multi-agent customer support system** for a fake e-commerce store. A user chats in natural language ("Where's my order?", "I want a refund for order 1003", "Cancel my order"). An **orchestrator agent** understands the request and routes it to the right **specialized sub-agent** (orders, refunds, payments, or FAQ). Each sub-agent **calls real tools** that read from and modify a backend (order database, payment service). If an agent can't complete a task, the system **handles the error gracefully and escalates to a human**. This demonstrates **agentic AI**: planning, tool-calling, multi-agent routing, and error handling — the skill the roadmap flags as the most important for an AI engineer.
**Why it's resume-worthy:** it's the Amazon-Rufus pattern. It shows LLMs *doing things*, not just answering — which is exactly what companies hire Gen AI engineers to build.
---
## 2. Feature list (the full scope)
**Core (must-have):**
1. Chat interface for the user.
2. **Orchestrator agent** that classifies intent and routes to a sub-agent.
3. **Specialized sub-agents**, each owning a domain:
   - **Order Agent** — look up order status, tracking, details.
   - **Refund Agent** — check eligibility, initiate a refund (modifies state).
   - **Payment Agent** — check payment status, handle a mock payment step.
   - **FAQ Agent** — answer general policy questions (shipping, returns policy).
4. **Tool calling** — agents call functions that hit a fake backend (read + write).
5. **Error handling** — retries on failure, and **escalation to a human** when the agent can't resolve.
6. **Conversation memory** — the agent remembers context within a chat (e.g., which order you're discussing).
7. Clean chat UI.
8. Deployed live with a public URL.
**Polish (what makes it stand out):**
9. **A visible "agent trace"** — show which agent handled the request and which tools it called (great for demos + shows you understand the flow).
10. **Guardrails** — the agent refuses actions it shouldn't do (e.g., refund an order that isn't delivered).
11. Token/cost tracking + response caching for FAQ answers.
12. Structured logging of agent decisions.
---
## 3. Tech stack (all free)
| Layer | Tool | Why |
|-------|------|-----|
| Language | **Python 3.10+** | Standard for AI |
| Agent framework | **LangGraph** (from LangChain) | Purpose-built for multi-agent + routing + state; the industry-standard keyword. (Alt: **CrewAI**.) |
| LLM | **Google Gemini** free tier (fallback **Groq**) | Free, supports tool/function calling |
| Fake backend | **SQLite** (via SQLAlchemy) or a simple JSON store | Free, local, gives the agent real state to change |
| API (optional) | **FastAPI** | If you want a backend/frontend split like Project 1 |
| UI | **Streamlit** | Fast chat UI; shows the agent trace nicely |
| Secrets | **python-dotenv** | Keep keys out of code |
| Hosting | **Streamlit Community Cloud** / **Hugging Face Spaces** / **Render** | Free deploy |
| Version control | **Git + GitHub** | Required for portfolio |
> Cost stays $0: the only paid thing would be LLM calls, and the free tier covers a demo. The backend is a local SQLite file — no cloud DB needed.
---
## 4. Architecture & flow
```
                          USER (chat)
                             │
                             ▼
                   ┌───────────────────┐
                   │  ORCHESTRATOR      │  ← classifies intent, routes,
                   │  (router agent)    │    holds conversation state
                   └─────────┬─────────┘
        ┌──────────┬─────────┼──────────┬───────────┐
        ▼          ▼         ▼           ▼           ▼
   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐  (no match / fails)
   │ ORDER  │ │ REFUND │ │PAYMENT │ │  FAQ   │        │
   │ agent  │ │ agent  │ │ agent  │ │ agent  │        ▼
   └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘   ┌──────────┐
       │ tools    │ tools    │ tools    │        │ ESCALATE │
       ▼          ▼          ▼          ▼        │ to human │
   ┌─────────────────────────────────────┐      └──────────┘
   │   FAKE BACKEND  (SQLite)             │
   │   orders · payments · refunds tables │
   └─────────────────────────────────────┘
```
**The loop for one message:**
1. User sends a message.
2. Orchestrator (LLM) decides the intent → picks a sub-agent.
3. Sub-agent (LLM) decides which **tool** to call and with what arguments.
4. Tool runs against the SQLite backend, returns real data / changes state.
5. Sub-agent turns the tool result into a natural-language reply.
6. If any step fails → retry, then **escalate to human** with a friendly message.
7. Show the agent trace (which agent, which tools) in the UI.
---
## 5. The fake backend (this is what makes it "agentic")
Create a small SQLite database seeded with sample data so the agent has real state to act on.
**Tables:**
- `orders`: `order_id, customer_name, item, status (placed/shipped/delivered/cancelled), order_date, amount`
- `payments`: `payment_id, order_id, status (pending/paid/refunded), method, amount`
- `refunds`: `refund_id, order_id, status (none/requested/approved/completed), reason`
**Seed** ~8–10 sample orders in various states so you can demo different paths (a delivered order that's refundable, a pending payment, a shipped order, etc.).
---
## 6. The tools (functions the agents call)
Each is a plain Python function with a clear signature and docstring (the LLM reads the docstring to decide when to use it):
```
get_order_status(order_id) -> dict          # Order Agent
get_order_details(order_id) -> dict          # Order Agent
track_shipment(order_id) -> dict             # Order Agent
check_refund_eligibility(order_id) -> dict   # Refund Agent (rule: only delivered orders)
initiate_refund(order_id, reason) -> dict    # Refund Agent (MODIFIES state)
get_payment_status(order_id) -> dict         # Payment Agent
process_payment(order_id, method) -> dict    # Payment Agent (MODIFIES state)
answer_faq(question) -> str                  # FAQ Agent (policy text / RAG-lite)
escalate_to_human(reason, context) -> dict   # any agent, on failure
```
**Guardrail example:** `initiate_refund` must first call `check_refund_eligibility`; if the order isn't delivered, it refuses and explains why. This shows you thought about safety, not just happy-path.
---
## 7. Project file structure
```
support-agent/
├── app.py                    # Streamlit chat UI + agent trace panel
├── src/
│   ├── __init__.py
│   ├── orchestrator.py       # router agent: intent -> sub-agent (LangGraph graph)
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── order_agent.py
│   │   ├── refund_agent.py
│   │   ├── payment_agent.py
│   │   └── faq_agent.py
│   ├── tools.py              # all tool functions (hit the SQLite backend)
│   ├── backend/
│   │   ├── db.py             # SQLite setup + SQLAlchemy models
│   │   └── seed.py           # seed sample orders/payments
│   ├── llm.py                # Gemini client + tool-calling + token counting
│   ├── memory.py             # conversation state
│   ├── errors.py             # retry + escalation logic
│   └── logging_config.py     # structured logging of agent decisions
├── tests/
│   ├── test_tools.py         # test each tool against a seeded test DB
│   └── test_routing.py       # test orchestrator routes intents correctly
├── requirements.txt
├── .env.example
├── .gitignore
├── Dockerfile
├── README.md
└── demo/                     # screenshots + demo video
```
---
## 8. Phase-by-phase build plan
> Build in order. Each phase ends in something that works. Don't advance until the current phase runs.
### Phase 0 — Setup
- Folder + `git init` + GitHub repo + venv + `requirements.txt` (see §9).
- `.gitignore` with `.env`, `venv/`, `__pycache__/`, `*.db`.
- Free **Gemini API key** in `.env`.
- ✅ **Done when:** `streamlit run app.py` shows a blank chat UI.
### Phase 1 — Fake backend + tools (no AI yet)
- Build the SQLite DB (`db.py`) and seed it (`seed.py`).
- Write the tool functions in `tools.py` and test them directly (call `get_order_status(1001)` and see real data).
- ✅ **Done when:** every tool works when called manually, and `initiate_refund` respects the eligibility rule.
### Phase 2 — Single agent with tool-calling
- `llm.py`: Gemini client that supports **function/tool calling**.
- Build ONE agent (Order Agent) that can call order tools based on a user message.
- Wire it to the chat UI.
- ✅ **Done when:** typing "where is order 1001?" makes the agent call `get_order_status` and reply naturally.
### Phase 3 — Multi-agent orchestration (the core)
- `orchestrator.py`: build a **LangGraph** graph. The orchestrator classifies intent and routes to Order / Refund / Payment / FAQ agents.
- Implement the other three sub-agents with their tools.
- ✅ **Done when:** different messages get routed to the correct agent, and refund/payment actions actually change the DB.
### Phase 4 — Memory + error handling + escalation
- `memory.py`: keep conversation context (remember the order under discussion).
- `errors.py`: retry a failed tool call once, then call `escalate_to_human` with a friendly message.
- ✅ **Done when:** a multi-turn chat works ("refund my last order" knows which order), and forcing a failure triggers graceful escalation.
### Phase 5 — Agent trace + guardrails + polish
- Show a side panel: which agent handled it, which tools were called, with what args.
- Enforce guardrails (no refund on undelivered orders, etc.).
- Add token tracking + cache FAQ answers + structured logging.
- ✅ **Done when:** the demo visibly shows the agent's reasoning path and refuses invalid actions.
### Phase 6 — Docker + README + deploy
- Write `Dockerfile`, `README.md` (see §11).
- Push to GitHub → deploy on Streamlit Cloud / HF Spaces (API key as a platform secret).
- ✅ **Done when:** a public URL works.
### Phase 7 — Backup demo
- Record a 60–90s demo: order lookup → refund (state changes) → a failure → escalation → show the trace.
- ✅ **Done when:** video is in `demo/` and linked in README.
---
## 9. requirements.txt (starting point)
```
streamlit
langgraph
langchain
langchain-google-genai
google-generativeai
sqlalchemy
python-dotenv
pydantic
```
(Swap in `groq` / `langchain-groq` if you use Groq instead of Gemini.)
---
## 10. Orchestrator routing prompt (starting point)
```
You are a customer-support router. Read the user's message and decide which
specialist should handle it. Respond with ONLY one word from this list:
- ORDER    : order status, tracking, order details
- REFUND   : refund requests, refund status, eligibility
- PAYMENT  : payment status, making a payment
- FAQ      : general policy questions (shipping times, return policy)
- ESCALATE : anything unclear, abusive, or outside the above
User message: {user_message}
Answer with one word only.
```
Sub-agents then use tool-calling: give the LLM the tool list + the user message, let it choose the tool and arguments, run the tool, and feed the result back for a final natural-language answer.
---
## 11. README.md template
```
# AI Customer Support Agent (Multi-Agent)
A multi-agent customer-support system for an e-commerce store. An orchestrator
routes each request to a specialist agent (orders, refunds, payments, FAQ) that
calls real backend tools to resolve it — with error handling and automatic
human-escalation on failure.
## Live demo
[link]  (video: demo/demo.mp4)
## What it does
- Understands natural-language support requests
- Routes to the right specialist agent (LangGraph orchestration)
- Calls tools that read AND modify a backend (order status, refunds, payments)
- Handles errors and escalates to a human when it can't resolve
- Shows an agent trace: which agent + which tools ran
## Tech
LangGraph multi-agent · Gemini tool-calling · SQLite backend · Streamlit
## How it works
Orchestrator classifies intent -> routes to a sub-agent -> sub-agent calls a
tool -> tool acts on the SQLite backend -> result becomes a natural-language
reply. Failures retry once, then escalate.
## Run locally
1. pip install -r requirements.txt
2. Add GEMINI_API_KEY to .env
3. python -m src.backend.seed   (creates + seeds the DB)
4. streamlit run app.py
## Cost
Runs on free-tier infrastructure ($0).
```
---
## 12. The "kickoff prompt" for Claude Code
> Save this spec into your project folder as `BUILD_SPEC.md`, then tell Claude Code:
```
Read BUILD_SPEC.md in this folder — it's the full spec for a multi-agent
customer support system (Python, LangGraph, Gemini tool-calling, SQLite
backend, Streamlit UI). The key point: agents must TAKE ACTIONS on the
backend, not just chat.
Build it phase by phase starting with Phase 0 and Phase 1 (setup + the
SQLite backend and tools, no AI yet). After each phase, explain what the
code does and how it works, then wait for me before continuing. Keep the
API key in .env and add .env to .gitignore.
```
**Important:** build phase by phase and make it explain each part. This project is more complex than Project 1 — you must understand the orchestration and tool-calling to defend it in interviews.
---
## 13. Testing / verification
- `test_tools.py`: each tool returns correct data from a seeded test DB; `initiate_refund` refuses ineligible orders.
- `test_routing.py`: the orchestrator routes sample messages to the correct agent.
- Manual: run each path (order, refund that changes state, payment, FAQ, a deliberate failure → escalation). Confirm the DB actually changes after a refund.
---
## 14. Resume bullet (write once deployed)
> *Built a multi-agent customer-support system (LangGraph, Gemini tool-calling) with an orchestrator routing requests to specialized order/refund/payment/FAQ agents that call backend tools to resolve them — including guardrails, error handling, and automatic human-escalation. SQLite backend, agent-trace UI, deployed live on free-tier infra.*
---
## 15. Interview prep — be able to explain these
- **What is an "agent" vs. a plain LLM call?** (An agent decides *actions* — which tool to call — in a loop, not just returns text.)
- **What is tool/function calling?** (The LLM outputs a structured request to run a function; you run it and feed the result back.)
- **Why multi-agent instead of one big agent?** (Separation of concerns, each agent is simpler, easier to debug, more reliable routing.)
- **What does the orchestrator do?** (Classifies intent and routes; holds conversation state.)
- **How do you handle errors / failures?** (Retry, then escalate to a human; guardrails block invalid actions.)
- **What is LangGraph and why use it?** (A framework to build agent workflows as a graph with state and routing.)
- **How do you stop the agent doing something harmful?** (Guardrails — e.g., eligibility check before a refund; escalation for anything unclear.)
- **Where's the state?** (SQLite backend; tools read and modify it — that's what makes actions real.)
---
## 16. Definition of done (Project 2 complete when…)
- [ ] All core features work; agents actually change backend state
- [ ] Error handling + escalation + guardrails in place
- [ ] Agent trace visible in the UI
- [ ] Tests pass
- [ ] Pushed to GitHub with a clean README
- [ ] Deployed live with a working public URL
- [ ] Backup demo video recorded
- [ ] You can explain everything in §15
- [ ] Resume bullet written and added
