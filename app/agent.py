
import os
from dotenv import load_dotenv

from agentscope.agent import Agent, ReActConfig
from agentscope.model import OpenAIChatModel
from agentscope.credential import OpenAICredential
from agentscope.tool import Toolkit, FunctionTool
from agentscope.state import AgentState
from agentscope.permission import PermissionContext, PermissionMode

from app.tools.product_tools import (
    search_products,
    get_product_details
)

load_dotenv()


def create_agent():

    # 1. Configure the LLM
    model = OpenAIChatModel(
        credential=OpenAICredential(
            api_key=os.environ["LLM_API_KEY"],
            base_url=os.environ["LLM_BASE_URL"],
        ),
        model=os.environ["LLM_MODEL_ID"],
    )

    # 2. Register tools
    toolkit = Toolkit(
        tools=[
            FunctionTool(
                search_products,
                is_read_only=True,
            ),
            FunctionTool(
            get_product_details,
            is_read_only=True
        )
        ]
    )

    # 3. Create the Agent
    agent = Agent(
        name="Globex",
        system_prompt=(
            "You are Globex, an AI shopping assistant. "
            "Use search_products to find products matching user requirements. "
            "When users request detailed comparisons, use get_product_details "
            "to retrieve additional information about the selected products. "
            "Respect the user's budget and requested number of products. "
            "Base your recommendations only on the retrieved product data. "
            "Do not invent product details or prices."
            """
            Product search rules:
            - The product tools access only the DummyJSON sample catalog,
            not a live German or global market database.
            - For laptop research, search the generic term "laptop" first.
            - If enough eligible products are found, retrieve their details
            without repeating searches.
            - Do not assume that brands relevant to a target market
            are necessarily available in the catalog.
            - Use only retrieved catalog evidence for product claims.
            """
        ),
        model=model,
        toolkit=toolkit,
        state=AgentState(
            permission_context=PermissionContext(
                mode=PermissionMode.EXPLORE
            )
        ),
        react_config=ReActConfig(max_iters=12),
    )

    return agent
