# Globex-Agent

**Adaptive Multi-Agent Product & Market Intelligence System**  
**Stage:** V1.0 portfolio prototype — core implementation complete; market-report end-to-end delivery not yet verified  
**Stack:** Python · AgentScope 2.x (`2.0.10` during development) · OpenAI-compatible LLM API · DummyJSON · SQLite · pytest

Globex-Agent is a CLI-based prototype for **catalog-grounded competitor research and product positioning analysis**. A Supervisor chooses among lightweight catalog lookup, detailed product research, and a sequential Research → Market Analysis workflow according to the task. The project focuses on **agent orchestration, tool integration, persistence, execution guardrails, and empirical evaluation** rather than a production e-commerce interface.

> **Data limitation:** DummyJSON is a demonstration product catalog, **not** a live German market intelligence source. Globex can compare catalog prices and descriptions; it cannot substantiate German market share, sales volumes, demand, or customer preferences from this source alone.

## Architecture

```text
User request (CLI / evaluation script)
             |
   Memory & Skill Context (optional)
   SQLite: brand profile, session history,
           reusable research instructions
             |
      Adaptive Supervisor (AgentScope)
             |
     +-------+--------------------+
     |       |                    |
     v       v                    v
Direct       Research Agent     Market Analysis Workflow
Search       |                    |
     |       +-> search_products()  +-> Research Agent
     |       +-> get_product_details()     |
     |                                 evidence text
     |                                    |
     |                               Market Agent
     |                                    |
     +-----------------+------------------+
                       |
                Supervisor response

Cross-cutting: TaskConstraints / ContextVar guardrails,
              delegation budget, error handling, eval logs
```

**Three execution paths**

- **Direct Search:** Simple listing requests call `search_products()` without spawning a Research Agent.
- **Research:** Detailed comparisons use a Research Agent with search and product-detail tools.
- **Market Analysis:** A deterministic Python workflow invokes Research first, passes the **textual research result** to a Market Analysis Agent, and returns a business-oriented, evidence-limited report. The Market Agent does not independently query the catalog.

This is **sequential agent handoff**, not autonomous agent-to-agent negotiation or a production market intelligence service.

## Features

| Capability | Implementation | Validation status |
|---|---|---|
| Catalog tools | `search_products(query, max_price, limit)`, `get_product_details(product_id)` using DummyJSON | Live agent use observed; failure behavior unit-tested |
| Adaptive routing | Supervisor delegates simple lookup, detailed research, or market analysis | S1 and R1 live runs succeeded; M1 chose market path |
| Persistent memory | SQLite brand profiles and session messages; context assembly | Offline tests passed; live-memory behavior not separately evaluated |
| Personal Skills | Save/update/load a text-based research workflow and insert into context | Offline tests passed; no web editor |
| Hard constraints | Extract selected English budget/quantity phrases; enforce limits in product search using `ContextVar` | Offline tests passed; final LLM prose is not independently validated |
| Execution guardrail | Limit Research Agent delegations within one task context | Offline tests passed |
| Report preservation | Write a successful Market Agent result to `evaluation/market_report_latest.md` | Code added; subsequent end-to-end verification pending |
| Evaluation | Fixed S1/R1/M1 cases, JSONL logs, latency and logged tool-call counts | Initial real-model runs recorded |

## Preliminary Evaluation (2026-10-25)

One observed run per configuration, **not** a statistically reliable benchmark. `Research calls` counts **Supervisor delegations**, not LLM API requests.

| Case | Variant | Time | Research delegations | Product searches | Detail calls | Outcome |
|---|---|---:|---:|---:|---:|---|
| S1: list up to 3 laptops under $1,500 | Adaptive | **8.98 s** | 0 | 1 | 0 | Completed; 3 eligible items returned |
| R1: compare exactly 2 laptops under $1,500 | Single Agent | **46.90 s** | n/a | 1 | 2 | Completed |
| R1: same request | Adaptive | **97.06 s** | 1 | 1 | 2 | Completed |
| M1: catalog-based competitor positioning | Adaptive | **238.16 s** | 1 | 5 | 2 | **Failed final delivery:** upstream idle timeout |

**What these runs show**

- S1 completed a simple listing without Research delegation or detail lookups. The exact `DIRECT_SEARCH` log marker should be verified against the saved JSONL record when reporting routing accuracy.
- In R1, both variants searched once and retrieved two product details. Adaptive took **50.16 s longer (~2.07× the elapsed time)** in these individual runs, consistent with orchestration overhead; more repetitions and API usage data would be needed for a robust performance claim.
- R1 answers respected the observed price/quantity limits, but some interpretations (e.g., inferred features or target users) went beyond explicit catalog evidence.
- In M1, logs confirmed `[ROUTE] MARKET_ANALYSIS`, `[ROUTE] RESEARCH_AGENT`, `[RESEARCH AGENT] Task returned`, and `[MARKET AGENT] Analysis returned`. **The final Supervisor API call did not complete**, so M1 is **not** an end-to-end success. Five searches included repeated generic laptop queries and attempts at market-related brand names not necessarily covered by DummyJSON.
- Input/output token counts and exact LLM call counts were **not measured**; tool-call counts must not be presented as token or API cost metrics.

See [`DEVLOG.md`](DEVLOG.md) for version history, limitations, failure analysis, and decisions. Real-run records are appended to `evaluation/results.jsonl` when evaluation is executed.

## Getting Started

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Configure the model connection in `.env` (names used by the implementation):

```dotenv
LLM_API_KEY=your_key_here
LLM_BASE_URL=your_openai_compatible_endpoint
LLM_MODEL_ID=your_model_id
```

Do not commit `.env` or real API keys. Free or upstream-hosted models may have quota limits, incompatibilities, or long response times.

Run the CLI:

```bash
python main.py
```

Run deterministic tests (no real LLM needed in the mocked tests):

```bash
python -m pytest tests/ -v
```

Inspect the evaluation cases without requesting an LLM:

```bash
python eval_v1.py --list
```

Run the single-agent baseline and adaptive routing evaluation (**these call real LLMs and may incur cost**):

```bash
python eval_v1.py --case R1 --variant single
python eval_v1.py --case R1 --variant adaptive
python eval_v1.py --case S1 --variant adaptive
python eval_v1.py --case M1 --variant adaptive
```

Results append to `evaluation/results.jsonl`. A successful Market Agent output can also be preserved in `evaluation/market_report_latest.md` in the updated market workflow. This artifact is not evidence that the Supervisor successfully delivered a final response.

## Repository Guide

```text
app/
  agent.py                 # Research Agent
  supervisor.py            # Supervisor, direct search, delegation, market workflow
  market_agent.py          # Evidence-based Market Analysis Agent
  guardrails.py            # Task constraints and delegation state
  tools/product_tools.py   # DummyJSON catalog tools
  memory/
    store.py               # SQLite persistence for profiles, sessions and Skills
    middleware.py          # Build context with saved memory and selected Skill
main.py                   # CLI entry point
eval_v1.py                # Fixed-task evaluation runner
tests/                     # Mocked offline tests
evaluation/                # Results generated during evaluation
DEVLOG.md                  # Engineering decisions and experiment notes
```

## Known Limitations / Scope

- **Prototype, not production:** No React/AG-UI UI, FastAPI deployment, user authentication, distributed job queue, or real market-data ingestion is claimed.
- **Memory scope:** SQLite session messages + explicitly saved brand preferences are not full AgentScope internal ReAct-state checkpointing. Model answers are not automatically promoted into long-term brand facts.
- **Skill scope:** Saved text instructions selected by ID; no dynamic executable skill sandbox or browser-based editor.
- **Guardrail scope:** Tool-level price/count limits cover the extractor's supported English patterns; they do **not** prove the final LLM answer always respects every user constraint.
- **Reliability:** The M1 timeout and redundant search behavior remain documented. Report preservation improves diagnosis, but is not yet a demonstrated end-to-end recovery mechanism.
- **Evaluation:** Preliminary runs only; token usage, repeatability, and genuine market outcomes remain unmeasured.

## Engineering Takeaway

The main lesson is that **adding agents is a trade-off**. Lightweight searches can avoid unnecessary delegation, while complex workflows benefit from separating evidence collection and business interpretation—but additional orchestration introduces latency, failure points, and opportunities for redundant tool calls. Globex makes those trade-offs observable through fixed tasks, guardrails, and engineering logs.
