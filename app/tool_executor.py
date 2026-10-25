from typing import Dict, Any
import os
from dotenv import load_dotenv
from app.tools.product_tools import (
    search_products,
    get_product_details
)


load_dotenv()


class ToolExecuter:
    def __init__(self):
        self.tools = {}
        
    #Put the tools into the toolbox.
    def tool_register(self, name, description,func):
        if name not in self.tools:
            self.tools[name] = {"description": description, "func":func}

    #After the LLM selects the appropriate tool, it retrieves the actual Python function based on the name.
    def getTool(self,name):
        return self.tools.get(name, {}).get("func")

    #tool list for llm：What tools are available, and what does each one do
    def toolavaliable(self):
        result = []

        for name, info in self.tools.items():
            result.append(f"-{name}: {info['description']}")

        return "\n".join(result)

# search tool

def search(query: str) -> str:
    try:
        from serpapi import GoogleSearch
        api_key = os.getenv("SERPAPI_API_KEY")

        params = {
            "engine" : "google",
            "q" : query,
            "api_key" : api_key,
            "gl": "de",  
            "hl": "en", 
        }
        client = GoogleSearch(params)

        result = client.get_dict()


        # print(result.keys())
        # print(result.keys())
        # print(type(result["organic_results"]))
        # print(result["organic_results"][0].keys())
        # print(result["organic_results"][0]["title"])
        if "answer_box_list" in result:
            return "\n".join(result["answer_box_list"])

        if "answer_box" in result and "answer" in result["answer_box"]:
            return result["answer_box"]["answer"]

        if "knowledge_graph" in result:
            return result["knowledge_graph"]["description"]

        if "organic_results" in result:
            snippets = []
            for res in result["organic_results"][:3]:
                title = res.get("title", "")
                snippet = res.get("snippet", "")
                snippets.append(title + "\n" + snippet)

            return "\n\n".join(snippets)

        return "dont find out"
    
    except Exception as e:
        return f"Error occurred when searching: {type(e).__name__}: {e}"

def add(a,b):
    return a+b

executor = ToolExecuter()

executor.tool_register("add", 
                       "add 2 numbers",
                       add)

executor.tool_register("search",
                       "A web search engine. Use this tool when you need to answer questions about current events, facts, and information not found in your knowledge base.",
                       search)
executor.tool_register(
    "search_products",
    "Search for products by keyword. "
    "Use this tool when the user wants to find or compare products.",
    search_products
)
