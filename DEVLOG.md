# Globex-Agent — Development Log

> **Project:** Adaptive Multi-Agent Product & Market Intelligence System  
> **Tech stack (current):** Python, AgentScope 2.x, DummyJSON API, SQLite, pytest  
> **Status:** V1.0 core implemented; offline tests passed; S1/R1 live runs succeeded; M1 final delivery failed after Research + Market handoff  
> **Last updated:** 2026-10-25

## Project direction

Globex began as a shopping-assistant prototype for product search and comparisons. The portfolio direction is now an **enterprise-oriented product and market intelligence system**, focusing on competitor research, product positioning, adaptive agent orchestration, memory, reusable skills, and reproducible evaluation.

**Current limitation:** DummyJSON is a sample product catalog, **not a source of real market intelligence**. The current prototype demonstrates agent orchestration, not verified market-share, consumer-trend, or regulatory findings.

---

## V0.1 — Single Agent and Tool Calling

**Goal:** Establish a working AgentScope agent that can use an external product-search tool.

**Implementation**
- Created the Python project and isolated `.venv` environment.
- Configured model credentials through `.env` and `OpenAIChatModel`.
- Created an AgentScope `Agent` with `ReActConfig` and a `Toolkit`.
- Registered `search_products()` via `FunctionTool`.
- Connected product lookup to the DummyJSON API.

**Learning / outcome**
- Understood the separation between **LLM decision-making**, **agent loop**, **tool execution**, and **external API**.
- Established a working single-agent baseline for later comparisons.

## V0.2 — Structured Product Search and Constraints

**Goal:** Support searches that include product category, budget, and quantity.

**Implementation**
- Extended `search_products(query, max_price=None, limit=5)`.
- Added a price filter (`max_price`) and output-size limit (`limit`).
- Clarified in the tool description that `query` should be a short keyword, while numeric budgets belong in `max_price`.

**Observations**
- Tool-argument definitions matter: an absent parameter caused earlier agent tool-call failures.
- A model may place a full user sentence into `query` instead of extracting the search keyword.

**Learning:** A tool schema and its description are part of the agent's interface contract.

## V0.3 — Multi-Tool Research Workflow

**Goal:** Let the agent use search results to retrieve detailed information for specific products.

**Implementation**
- Added `get_product_details(product_id)`.
- Registered both `search_products()` and `get_product_details()` in the AgentScope `Toolkit`.
- Tested the sequence: **search products → identify product IDs → retrieve details → compare results**.

**Verified observation**
- A laptop-comparison run successfully chained product search with detail lookups.
- The model sometimes retrieved more products than requested, motivating explicit efficiency and constraint checks.

**Learning:** Tool chaining works, but correct orchestration must be measured rather than assumed.

## V0.4 — Basic Harness Reliability and Unit Testing

**Goal:** Avoid uncontrolled crashes when external catalog requests fail.

**Implementation**
- Added exception handling for API timeout, HTTP errors, and request failures in product tools.
- Return explicit `TOOL_ERROR: ...` messages for supported failure cases.
- Added a `pytest` unit test using `unittest.mock.patch` to simulate `requests.Timeout` without an actual network delay.

**Verified test (2026-10-24)**
```text
python -m pytest tests/test_product_tools.py -v
tests/test_product_tools.py::test_search_timeout PASSED [100%]
1 passed in 0.08s
```

**Limits / TODO**
- Only the timeout test is confirmed passing in the recorded output. A proposed 404 test has **not yet been confirmed**.
- Returning an error string does **not** by itself guarantee automatic retry, recovery, or correct agent-level decisions.
- Add broader error tests and agent-level failure-handling checks later.

**Learning:** Distinguish **tool reliability**, **agent recovery**, and **end-to-end success**.

## V0.5 — Supervisor + Research Agent

**Goal:** Verify the **SubAgent as Tool** pattern before building adaptive routing.

**Implementation**
- Added `app/supervisor.py`.
- Created `consult_research_agent(task)` as an async `FunctionTool`.
- Reused `create_agent()` to create the Research Agent with its own ReAct loop and product tools.
- Created a Supervisor Agent whose Toolkit exposes `consult_research_agent()`.
- Connected the Supervisor to `main.py`.

**Verified run (2026-10-24)**
- **3** Supervisor → Research Agent delegations.
- **6** logged `search_products()` calls.
- **6** logged `get_product_details()` calls.
- Research results returned successfully, and Supervisor generated a final answer.

**Conclusion:** The nested execution chain works: **User → Supervisor → Research Agent → Product Tools → Supervisor → User**. This validates delegation, **not yet adaptive routing**.

### Issues discovered in the V0.5 run

| Issue | Evidence from run | Why it matters | Planned mitigation |
|---|---|---|---|
| **Constraint Preservation** | User requested **2 laptops under $1,500**, but Supervisor returned **3** and one delegation broadened the search to **$1,750**. | The agent changed hard requirements without permission. | Add explicit constraint-preservation rules; later validate quantity/budget in code and tests. |
| **Redundant Tool Calls** | Three delegations and repeated searches/details were needed for one comparison task. | Higher latency and potential model/tool costs. | Improve task delegation, avoid repeated retrieval, cache reusable structured evidence where useful, and evaluate tool-call counts. |
| **Agent State Management** | `create_agent()` creates a new Research Agent for each delegation. | The next delegation does not automatically reuse the previous Research Agent's internal state. | Design explicit state handoff and later SQLite session persistence; do not assume persistence already exists. |
| **Evidence Grounding** | Final answer claimed one laptop had the “most powerful performance” without presenting sufficient comparative performance evidence. | Unsupported conclusions can be misleading, especially in business research. | Restrict claims to retrieved evidence; preserve sources and state when data is insufficient. |

**Follow-up:** The later V0.9 tool-level guardrails address selected price/quantity constraints and repeated Research delegation. They do not yet validate all final-answer claims or eliminate repeated searches inside Research. Historical figures above describe V0.5, before these fixes.

---

## V0.6 — Adaptive Routing and Sequential Market Analysis

**Goal:** Route simple queries through a lightweight lookup and complex requests to role-specific agents.

**Implementation**
- Added `quick_catalog_lookup()` as a Supervisor tool for direct catalog retrieval.
- Kept `consult_research_agent()` for multi-step product investigation.
- Added `create_market_agent()` in `app/market_agent.py` and `research_and_analyze_market()` in `app/supervisor.py`.
- The market workflow runs **Research Agent → textual evidence handoff → Market Analysis Agent**. Market Agent operates on passed evidence rather than searching independently.
- Registered three Supervisor paths: `DIRECT_SEARCH`, `RESEARCH_AGENT`, `MARKET_ANALYSIS`.

**Testing / observations**
- Direct-search path was demonstrated with simple laptop listings.
- Three mocked market-workflow tests passed: successful evidence handoff, empty research result, and research tool-error propagation.
- Earlier real-model trials encountered repetitive/malformed tool-call text and API rate limits; Mock tests could not establish model-level stability.

**Design decision:** Keep sequential orchestration explicit in Python. Do not claim production-grade market intelligence or inferred facts unsupported by the DummyJSON catalog.

## V0.7 — SQLite Memory and Session History

**Goal:** Persist small amounts of business context across CLI program runs.

**Implementation**
- Added `app/memory/store.py` with SQLite-backed `brand_profiles` and `session_messages`.
- Added `app/memory/middleware.py` to assemble brand profile, recent session messages, and current user request into an agent-readable context.
- Used stable `profile_id` / `session_id` for retrieval; test databases use `tmp_path` and `monkeypatch` to avoid overwriting working data.

**Offline tests reported passed**
- Save/load brand profile.
- Update existing brand profile.
- Preserve session history order.
- Include stored memory in generated agent context.

**Limits:** This is application-level persistence, not full restoration of AgentScope's internal state or verified live LLM recall. Do not turn an Agent's own market-analysis answer into an automatically trusted user preference.

## V0.8 — Reusable Personal Skills

**Goal:** Allow a brand to save and reuse a preferred research-report workflow.

**Implementation**
- Added the `personal_skills` SQLite table and `save_skill()` / `load_skill()` functions.
- Extended `build_memory_context(..., skill_id=...)` to add an explicitly selected Skill's title and instructions.
- Kept Skills as editable **stored text workflows**, not executable code and not a web-based editor.

**Offline tests reported passed**
- Save and load Skill.
- Update a saved Skill.
- Insert Skill instructions into context.
- Return `None` for an unknown Skill.

**Limit:** The live model's adherence to Skills was not separately measured.

## V0.9 — Task Constraints and Execution Guardrails

**Goal:** Reduce the constraint drift and repeated delegation observed in V0.5.

**Implementation**
- Added `app/guardrails.py` with `TaskConstraints`, a lightweight English-language extractor, and `ContextVar` task scope.
- Enforced selected maximum-price and per-search item-count limits in `search_products()` by applying current task constraints.
- Added `ExecutionState` and `claim_research_call()`; the managed CLI request permits at most one Research Agent delegation.
- Kept the existing timeout/HTTP exception handling in product tools.

**Offline tests reported passed**
- Five constraint tests: extract budget/count, reject budget expansion, restore missing budget, reset task context, and enforce constraints inside a mocked product search.
- Two delegation tests: block a second Research call in one request and reset the budget for the next request.
- User reported that the full `pytest` suite passed **before** the later market-report file-saving edit; that newest edit has not been separately confirmed by a fresh test run.

**Limits / trade-offs**
- Recognizes only a subset of English patterns (`under $1500`, `exactly two`, etc.); not a general semantic constraint parser.
- A per-search limit does not ensure the final LLM response contains exactly the right number of distinct products.
- One permitted delegation does not limit the number of searches **inside** that Research Agent.
- `ContextVar` is request-scoped in the managed CLI path; it is not a durable global rate limiter.

## V1.0 — Fixed-Task Evaluation and Delivery

**Goal:** Compare the single-agent baseline to adaptive routing, document outcomes, and stop feature expansion.

**Evaluation runner**
- Added `eval_v1.py` with fixed S1 (simple lookup), R1 (two-product research), and M1 (catalog-based business positioning) tasks.
- Records execution time, routing markers, logged search/detail counts, answer/error text, and captured logs in `evaluation/results.jsonl`.
- Real runs call the LLM; `--list` and mocked `pytest` tests do not.

### Observed real-model runs (2026-10-25)

| Case | Variant | Latency | Research delegations | Search calls | Detail calls | Result |
|---|---|---:|---:|---:|---:|---|
| S1 | Adaptive | 8.98 s | 0 | 1 | 0 | Complete: 3 laptops below $1,500 |
| R1 | Single | 46.90 s | n/a | 1 | 2 | Complete: 2 eligible laptops compared |
| R1 | Adaptive | 97.06 s | 1 | 1 | 2 | Complete: same core task |
| M1 | Adaptive | 238.16 s | 1 | 5 | 2 | **APIError: Upstream idle timeout exceeded** |

**Interpretation**
- **S1:** Completed without Research delegation or detail lookup, consistent with a lightweight direct path. The `DIRECT_SEARCH` marker's count should be checked in saved logs before publishing a precise routing accuracy figure.
- **R1:** Both variants used one search and two detail calls. Adaptive required an additional **50.16 s (~2.07× single-agent elapsed time)** in these single trials. This supports an **observed orchestration cost**, not a general statistical conclusion or verified API-cost increase.
- **R1 grounding:** Prices and counts met the visible constraints. Some descriptions expanded source evidence into interpretations (e.g., inferred hardware feature / target users), so complete factual grounding is **not** established.
- **M1:** Both specialist steps completed, but the end-to-end task **failed to deliver a final answer**. Market Report content and quality were not preserved in the failed run, so they were **not** reviewed for correctness.

### M1 failure investigation

The saved log showed:

```text
[ROUTE] MARKET_ANALYSIS
[ROUTE] RESEARCH_AGENT
[DEBUG] query=Tuxedo laptop, max_price=1500, limit=2
[DEBUG] query=Schenker laptop, max_price=1500, limit=2
[DEBUG] query=laptop, max_price=1500, limit=2
[DEBUG] query=laptop, max_price=1500, limit=2
[DEBUG] query=Medion laptop, max_price=1500, limit=2
[RESEARCH AGENT] Task returned
[MARKET AGENT] Analysis returned
[ERROR] APIError: Upstream idle timeout exceeded
```

**Diagnosis**
1. Supervisor selected the intended market workflow; Research returned; Market Agent returned.
2. The timeout occurred **after** those completion markers, most likely while the Supervisor awaited its final model response. Logs support this inference, but no per-LLM-call tracing was captured.
3. Research made five searches for a task requiring two products, including identical generic `laptop` searches and market-related brand names absent from the catalog's guaranteed coverage. Target-market reasoning was conflated with the sample catalog's search scope.

**Changes after diagnosis**
- Proposed / discussed Research prompt guidance: search generic `laptop` first, do not assume market-specific brands exist in DummyJSON, and avoid repeat searches when enough eligible evidence exists. **Effectiveness not re-evaluated.**
- Updated the market workflow to preserve a successful Market Agent result in `evaluation/market_report_latest.md` before returning to Supervisor, including restoration of the missing `response = await market_agent.reply(...)` line after an edit error. **No subsequent successful M1 or post-edit pytest result has been reported.**
- Do **not** classify this as end-to-end success or proven automatic timeout recovery; the change provides a local intermediate artifact on later successful market-agent runs.

### Final assessment

**Implemented:** Adaptive Supervisor, research and market agents, catalog tools, SQLite-based memory and Skills, scoped guardrails, and a fixed-task evaluation runner.

**Verified offline:** Memory/Skills/Guardrail and mocked market-handoff tests (user reported passes).

**Verified in real runs:** S1 direct-style lightweight completion; R1 single-agent and adaptive comparison; M1 Research → Market Agent execution sequence.

**Not verified:** M1 final response after Supervisor timeout, repeatable performance distributions, precise LLM call/token costs, complete final-answer fact checking, post-edit regression tests, and browser-based Skill management.

**Scope decision:** Stop adding V1.1 features; prioritize README, project explanation, CV and interview-ready failure/trade-off analysis. This is a portfolio prototype, not a deployed production system.

---

## Evaluation template (append after each important experiment)

```text
Date:
Version / commit:
User task:
Expected behavior:
Observed behavior:
Tool calls / delegations:
Latency / tokens (if measured):
Issue:
Hypothesis:
Change made:
Retest outcome:
```

## Documentation rule

- `README.md`: concise project overview, architecture, setup, demo, and validated results.
- `DEVLOG.md`: development history, debugging, decisions, experiments, and lessons learned.
- Keep **implemented**, **tested**, and **planned** claims clearly separate.
