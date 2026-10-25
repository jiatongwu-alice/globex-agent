
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.guardrails import (
    TaskConstraints,
    use_task_constraints
)

from app.supervisor import consult_research_agent


def test_research_delegation_limit():
    """Only one research delegation is allowed per request."""

    research_agent = MagicMock()
    response = MagicMock()

    response.get_text_content.return_value = (
        "Research completed."
    )

    research_agent.reply = AsyncMock(
        return_value=response
    )

    async def run_two_calls():
        first = await consult_research_agent("Task A")
        second = await consult_research_agent("Task B")
        return first, second

    with patch(
        "app.supervisor.create_agent",
        return_value=research_agent
    ):
        with use_task_constraints(TaskConstraints()):
            first, second = asyncio.run(run_two_calls())

    assert first == "Research completed."
    assert second == (
        "TOOL_ERROR: Research delegation limit exceeded."
    )

    research_agent.reply.assert_awaited_once()


def test_execution_state_resets():
    """A new user request gets a fresh research budget."""

    research_agent = MagicMock()
    response = MagicMock()

    response.get_text_content.return_value = "Research completed."
    research_agent.reply = AsyncMock(return_value=response)

    with patch(
        "app.supervisor.create_agent",
        return_value=research_agent
    ):
        with use_task_constraints(TaskConstraints()):
            first = asyncio.run(
                consult_research_agent("Task A")
            )

        with use_task_constraints(TaskConstraints()):
            second = asyncio.run(
                consult_research_agent("Task B")
            )

    assert first == "Research completed."
    assert second == "Research completed."

    assert research_agent.reply.await_count == 2
