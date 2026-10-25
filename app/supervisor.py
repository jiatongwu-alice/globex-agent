
import os
from dotenv import load_dotenv

from agentscope.agent import Agent, ReActConfig
from agentscope.model import OpenAIChatModel
from agentscope.credential import OpenAICredential
from agentscope.tool import Toolkit, FunctionTool
from agentscope.message import UserMsg
from agentscope.state import AgentState
from agentscope.permission import PermissionContext, PermissionMode

from app.agent import create_agent
from app.tools.product_tools import search_products
from app.market_agent import create_market_agent
from app.guardrails import claim_research_call
from pathlib import Path

load_dotenv()

# Describe the tool's purpose to guide Supervisor routing.
# Log the selected route for debugging.
def quick_catalog_lookup(
    query: str,
    max_price: float | None = None,
    limit: int = 5
) -> str:
    """Quickly look up products without starting another agent.

    Use for simple catalog searches requiring only
    product names, categories, and prices.

    Args:
        query: A short product keyword, such as laptop.
        max_price: Maximum allowed product price in USD.
        limit: Maximum number of products to return.
    """
    print("[ROUTE] DIRECT_SEARCH")

    return search_products(
        query=query,
        max_price=max_price,
        limit=limit
    )



# delegate a task to the Research Agent

async def consult_research_agent(task: str) -> str:
    """Delegate product research to the Research Agent.

    Args:
        task: Product research request and constraints.
    """

    # Prevent redundant research delegations
    if not claim_research_call():
        print("[GUARDRAIL] Research delegation blocked")
        return "TOOL_ERROR: Research delegation limit exceeded."

    print("[ROUTE] RESEARCH_AGENT")
    print(f"[SUPERVISOR] Delegating: {task}")

    research_agent = create_agent()

    response = await research_agent.reply(
        UserMsg(name="user", content=task)
    )

    result = response.get_text_content()

    print("[RESEARCH AGENT] Task returned")

    return result



async def research_and_analyze_market(task: str) -> str:
    """Research products and analyze their market positioning.

    Use for competitor analysis, pricing strategy, and
    evidence-based product positioning tasks.

    Args:
        task: Complete business research request, including
            product category, target market, and constraints.
    """
    print("[ROUTE] MARKET_ANALYSIS")

    # Collect product evidence
    research_result = await consult_research_agent(task)

    if not research_result.strip():
        return "TOOL_ERROR: No research evidence was returned."
    if research_result.strip().startswith("TOOL_ERROR:"):
        return research_result.strip()

    # Create the Market Analysis Agent
    market_agent = create_market_agent()

    #  Explicitly pass the evidence to the analyst
    analysis_task = (
        f"Original business request:\n{task}\n\n"
        f"Product research evidence:\n{research_result}\n\n"
        "Data source: DummyJSON sample product catalog.\n"
        "Analyze only what this evidence supports. "
        "Distinguish catalog-based positioning from "
        "unverified real-market claims."
    )
    #Combine the initial business tasks with the research findings and hand them over to the Market Analysis Agent.

    response = await market_agent.reply(
        UserMsg(name="user", content=analysis_task)
    )

    # Extract the analysis report
    result = response.get_text_content()

    print("[MARKET AGENT] Analysis returned")

    # Preserve the report even if Supervisor later fails
    output = Path("evaluation/market_report_latest.md")
    output.parent.mkdir(parents=True, exist_ok=True)

    output.write_text(result, encoding="utf-8")

    print(f"[MARKET AGENT] Report saved to {output}")

    return result

def create_supervisor():

    model = OpenAIChatModel(
        credential=OpenAICredential(
            api_key=os.environ["LLM_API_KEY"],
            base_url=os.environ["LLM_BASE_URL"],
        ),
        model=os.environ["LLM_MODEL_ID"],
    )

    toolkit = Toolkit(
        tools=[
            FunctionTool(
            quick_catalog_lookup,
            is_read_only=True
        ),
            FunctionTool(
                consult_research_agent,
                is_read_only=True
            ),
            FunctionTool(
                            research_and_analyze_market,
                            is_read_only=True
                        )
        ]
    )

    supervisor = Agent(
        name="Supervisor",
        system_prompt=(
            "You are the Supervisor of Globex, an adaptive "
            "product and market intelligence agent system. "

            "Select exactly one primary execution route "
            "according to the user's task. "

            "ROUTING RULES: "

            "1. For simple product searches requiring only names, "
            "categories, or prices, use quick_catalog_lookup. "

            "2. For detailed product research or specification "
            "comparisons, use consult_research_agent. "

            "3. For competitor analysis, pricing positioning, "
            "business strategy, or market intelligence requests, "
            "use research_and_analyze_market. "

            "The market analysis tool already runs the Research "
            "Agent before the Market Analysis Agent. "
            "Do not separately repeat those steps. "

            "Preserve all user constraints, including budget, "
            "quantity, category, and target market. "

            "Never expand the user's budget without permission. "
            "Do not repeat research unless essential evidence "
            "is missing. "

            "Use only supported evidence. "
            "Never invent market data or technical specifications. "

            "When information is missing, explain the limitation."
        ),
        model=model,
        toolkit=toolkit,
        state=AgentState(
            permission_context=PermissionContext(
                mode=PermissionMode.EXPLORE
            )
        ),
        react_config=ReActConfig(max_iters=5),
    )

    return supervisor
