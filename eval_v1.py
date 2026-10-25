
import argparse
import asyncio
import io
import json
import time

from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

from agentscope.message import UserMsg

from app.agent import create_agent
from app.supervisor import create_supervisor
from app.guardrails import (
    extract_constraints,
    use_task_constraints,
)


# Fixed evaluation tasks
CASES = {
    "S1": {
        "category": "simple",
        "task": (
            "List up to three laptops under $1500. "
            "Show only their names and prices. "
            "No comparison is needed."
        ),
        "expected_route": "DIRECT_SEARCH",
    },
    "R1": {
        "category": "research",
        "task": (
            "Research exactly two laptops under $1500. "
            "Retrieve their product details and compare "
            "their prices and features. "
            "Use only evidence from the product catalog."
        ),
        "expected_route": "RESEARCH_AGENT",
    },
    "M1": {
        "category": "market",
        "task": (
            "For a Germany-focused brand, research exactly "
            "two laptops under $1500. Analyze their competitor "
            "pricing and product positioning using catalog "
            "evidence only. Do not invent market share or "
            "consumer demand data."
        ),
        "expected_route": "MARKET_ANALYSIS",
    },
}


async def evaluate(case_id: str, variant: str):
    case = CASES[case_id]
    task = case["task"]

    captured_logs = io.StringIO()
    answer = ""
    error = None

    start = time.perf_counter()

    # Capture existing debug output and routing logs.
    with redirect_stdout(captured_logs):
        try:
            constraints = extract_constraints(task)

            with use_task_constraints(constraints):
                agent = (
                    create_supervisor()
                    if variant == "adaptive"
                    else create_agent()
                )

                response = await agent.reply(
                    UserMsg(name="user", content=task)
                )

                answer = response.get_text_content() or ""

        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"

    elapsed = time.perf_counter() - start
    logs = captured_logs.getvalue()

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "case_id": case_id,
        "category": case["category"],
        "variant": variant,
        "expected_route": case["expected_route"],
        "task": task,
        "elapsed_seconds": round(elapsed, 2),
        "research_delegations": logs.count(
            "[ROUTE] RESEARCH_AGENT"
        ),
        "market_analysis_calls": logs.count(
            "[ROUTE] MARKET_ANALYSIS"
        ),
        "direct_search_calls": logs.count(
            "[ROUTE] DIRECT_SEARCH"
        ),
        "product_search_calls": logs.count(
            "[DEBUG] query="
        ),
        "product_detail_calls": logs.count(
            "[TOOL] Getting product details:"
        ),
        "answer": answer,
        "error": error,
        "logs": logs[-12000:],
    }

    output = Path("evaluation/results.jsonl")
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(result, ensure_ascii=False) + "\n"
        )

    print(f"\nCase: {case_id}")
    print(f"Variant: {variant}")
    print(f"Execution time: {elapsed:.2f}s")
    print(f"Research calls: {result['research_delegations']}")
    print(f"Product searches: {result['product_search_calls']}")
    print(f"Product details: {result['product_detail_calls']}")

    if error:
        print(f"\n[ERROR] {error}")
    else:
        print("\n--- Final Answer ---")
        print(answer)

    print(f"\nSaved to: {output}")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--case",
        choices=sorted(CASES)
    )
    parser.add_argument(
        "--variant",
        choices=["single", "adaptive"],
        default="adaptive"
    )
    parser.add_argument(
        "--list",
        action="store_true"
    )

    args = parser.parse_args()

    if args.list:
        for case_id, case in CASES.items():
            constraints = extract_constraints(case["task"])

            print(
                f"{case_id}: {case['category']} | "
                f"{constraints}"
            )
        return

    if args.case is None:
        parser.error("--case is required unless --list is used")

    asyncio.run(evaluate(args.case, args.variant))


if __name__ == "__main__":
    main()
