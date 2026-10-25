
import asyncio
import time

from openai import RateLimitError
from agentscope.message import UserMsg

from app.supervisor import create_supervisor
from app.memory.store import init_db, save_message
from app.memory.middleware import build_memory_context
from app.guardrails import (
    extract_constraints,
    use_task_constraints
)


# Use stable IDs to load the same memory across program runs.
PROFILE_ID = "demo_brand"
SESSION_ID = "demo_session"


async def main():
    # Initialize SQLite
    init_db()

    # Get the current user request
    user_text = (
        "Analyze two laptop competitors for our brand. "
        "Compare their prices and product positioning."
    )

    #Load and prepare memory context
    context = build_memory_context(
    profile_id=PROFILE_ID,
    session_id=SESSION_ID,
    user_text=user_text,
    skill_id="competitor_analysis"
)

    print("[MEMORY] Context loaded")

    # Send the memory-enriched request to Supervisor
    agent = create_supervisor()

    message = UserMsg(
        name="user",
        content=context
    )

    start_time = time.perf_counter()

    try:
        constraints = extract_constraints(user_text)

        print(f"[GUARDRAIL] Active constraints: {constraints}")

        with use_task_constraints(constraints):
            response = await agent.reply(message)

    except RateLimitError:
        print("[ERROR] LLM rate limit exceeded.")
        return

    elapsed_time = time.perf_counter() - start_time

    result = response.get_text_content()

    print("\n--- Agent Response ---")
    print(result)
    print(f"[METRIC] Execution time: {elapsed_time:.2f}s")

    # Save the conversation after a successful reply
    if result and result.strip():
        save_message(SESSION_ID, "user", user_text)
        save_message(SESSION_ID, "assistant", result)

        print("[MEMORY] Conversation saved")


if __name__ == "__main__":
    asyncio.run(main())

