import json
import requests
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import ToolNode
from shared.config import Config

@tool
def tavily_search_mcp(query: str) -> str:
    """Searches the web to find context on obscure company names or niche tech stacks."""
    return f"Context result for query: {query}"

@tool
def github_stats_mcp(repo_path: str) -> str:
    """Fetches live star and fork counts from GitHub API given 'owner/repo'."""
    url = f"https://api.github.com/repos/{repo_path}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            return json.dumps({
                "stars": data.get("stargazers_count", 0),
                "forks": data.get("forks_count", 0),
                "language": data.get("language", "Unknown")
            })
    except Exception:
        pass
    return json.dumps({"stars": 0, "forks": 0, "language": "Unknown"})

tools = [tavily_search_mcp, github_stats_mcp]
tool_node = ToolNode(tools)

parser_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", 
    temperature=0.2,
    google_api_key=Config.GOOGLE_API_KEY
).bind_tools(tools)

def parser_node(state: dict) -> dict:
    """Agent 1: Parses resume text into structured JSON according to domain criteria."""
    messages = state.get("messages", [])
    new_messages = []
    
    if not messages:
        sys_msg = SystemMessage(content="""
        You are an expert Technical Resume Parser. Extract resume details into JSON.
        
        CRITICAL CONTENT RULES:
        - When extracting professional experience (e.g., Resideo, Niar), strictly REMOVE all quality assurance and test automation references.
        - Emphasize Data Engineering and Analytics tasks, architectures, Apache Spark, AWS, Snowflake, Pandas, and SQL.
        - Extract education prominently.
        - Output ONLY valid raw JSON at the end.
        """)
        human_msg = HumanMessage(content=f"Parse the following resume content:\n\n{state.get('resume_text', '')}")
        messages = [sys_msg, human_msg]
        new_messages.extend([sys_msg, human_msg])

    response = parser_llm.invoke(messages)
    new_messages.append(response)
    
    enriched_json = ""
    if not response.tool_calls:
        try:
            clean_text = response.content.replace("```json", "").replace("```", "").strip()
            json.loads(clean_text)
            enriched_json = clean_text
        except Exception as e:
            print(f"Warning: JSON parsing failed - {e}")

    return {"messages": new_messages, "enriched_json": enriched_json}
