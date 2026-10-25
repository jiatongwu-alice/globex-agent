
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.supervisor import research_and_analyze_market


def test_research_evidence_handoff():
    """Research evidence must reach the Market Agent."""

    # Simulate a successful research result
    research_evidence = (
        "Lenovo Yoga 920 costs $1099.99. "
        "Dell XPS 13 costs $1499.99."
    )

    # Simulate the Market Agent
    market_agent = MagicMock()
    fake_response = MagicMock()

    fake_response.get_text_content.return_value = (
        "Competitor price comparison completed."
    )

    market_agent.reply = AsyncMock(
        return_value=fake_response
    )

    with (
        patch(
            "app.supervisor.consult_research_agent",
            new_callable=AsyncMock
        ) as mock_research,
        patch(
            "app.supervisor.create_market_agent",
            return_value=market_agent
        )
    ):
        mock_research.return_value = research_evidence

        result = asyncio.run(
            research_and_analyze_market(
                "Compare laptop competitor pricing."
            )
        )

        # Both agents must participate
        mock_research.assert_awaited_once()
        market_agent.reply.assert_awaited_once()

        # Inspect the message sent to Market Agent
        market_message = market_agent.reply.await_args.args[0]
        market_input = str(market_message.content)

        assert "Lenovo Yoga 920" in market_input
        assert "1099.99" in market_input
        assert "Dell XPS 13" in market_input

        assert result == (
            "Competitor price comparison completed."
        )


def test_empty_research_result():
    """Market analysis must stop if evidence is empty."""

    with (
        patch(
            "app.supervisor.consult_research_agent",
            new_callable=AsyncMock
        ) as mock_research,
        patch(
            "app.supervisor.create_market_agent"
        ) as mock_create_market
    ):
        mock_research.return_value = ""

        result = asyncio.run(
            research_and_analyze_market(
                "Analyze laptop pricing."
            )
        )

        assert result == (
            "TOOL_ERROR: No research evidence was returned."
        )

        # Market Agent must not be created
        mock_create_market.assert_not_called()


def test_research_tool_error():
    """Market analysis must stop after a research error."""

    with (
        patch(
            "app.supervisor.consult_research_agent",
            new_callable=AsyncMock
        ) as mock_research,
        patch(
            "app.supervisor.create_market_agent"
        ) as mock_create_market
    ):
        mock_research.return_value = (
            "TOOL_ERROR: Product search timed out."
        )

        result = asyncio.run(
            research_and_analyze_market(
                "Analyze laptop pricing."
            )
        )

        assert result == (
            "TOOL_ERROR: Product search timed out."
        )

        mock_create_market.assert_not_called()
