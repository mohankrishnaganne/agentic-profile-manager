import os
import json
import requests
from typing import TypedDict, Annotated, List
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

# ==========================================
# 1. DEFINE THE STATE
# ==========================================
class PortfolioState(TypedDict):
    """The shared memory object passed between all agents."""
    messages: Annotated[List[BaseMessage], add_messages]
    resume_path: str
    github_token: str
    vercel_token: str
    enriched_json: str  # Agent 1 will populate this
    site_code: str      # Agent 2 will populate this
    live_url: str       # Agent 3 will populate this

# ==========================================
# 2. DEFINE THE MCP TOOLS (Mocked as LangChain Tools for MVP)
# ==========================================
@tool
def read_file_mcp(file_path: str) -> str:
    """Reads the raw text from the uploaded PDF/DOCX resume."""
    # In reality, you'd use PyPDF2 or python-docx here.
    return """
    Name: Alex Developer
    Experience: 
    - Software Engineer at Vercator (2022-2024). Built point-cloud systems.
    - Implemented PBFT consensus mechanisms.
    Projects:
    - Built fast-cache (github.com/alex/fast-cache)
    """

@tool
def tavily_search_mcp(query: str) -> str:
    """Searches the web to find context on obscure company names or expand tech jargon."""
    # MVP Mock: Replace with actual requests.post("https://api.tavily.com/search")
    print(f"[Tool: Tavily] Searching for: {query}")
    if "Vercator" in query:
        return "Vercator is an innovative UK startup specializing in 3D spatial data and point-cloud processing."
    if "PBFT" in query:
        return "Practical Byzantine Fault Tolerance (PBFT) is a high-performance distributed consensus algorithm."
    return "No specific data found."

@tool
def github_stats_mcp(repo_path: str) -> str:
    """Fetches live star and fork counts from the GitHub API. Input format: 'owner/repo'"""
    print(f"[Tool: GitHub] Fetching stats for: {repo_path}")
    url = f"https://api.github.com/repos/{repo_path}"
    
    # Optional: use a token if provided to avoid rate limits
    headers = {"Accept": "application/vnd.github.v3+json"}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return json.dumps({
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "language": data.get("language", "Unknown")
        })
    # Fallback for MVP testing if repo doesn't exist
    return json.dumps({"stars": 1420, "forks": 180, "language": "C++"})

tools = [read_file_mcp, tavily_search_mcp, github_stats_mcp]
tool_node = ToolNode(tools)

# ==========================================
# 3. DEFINE THE PARSER AGENT NODE
# ==========================================
# Set your OpenAI API Key in your environment variables
llm = ChatOpenAI(model="gpt-4o", temperature=0.2).bind_tools(tools)

def parser_node(state: PortfolioState):
    """Agent 1: Reads resume, uses tools to enrich data, outputs JSON."""
    
    system_prompt = SystemMessage(content="""
    You are an expert tech recruiter and data parser. Your job is to extract resume data into a rich JSON format.
    
    Instructions:
    1. Read the provided resume file.
    2. Identify any unknown companies or niche tech jargon and use the `tavily_search_mcp` tool to explain them.
    3. Identify any GitHub project links and use the `github_stats_mcp` tool to fetch their star/fork counts.
    4. Compile the final result into a structured JSON string containing: 'name', 'experience' (with enriched descriptions), and 'projects' (with star metrics).
    
    Output ONLY valid JSON in your final message once you have gathered all the data.
    """)

    # If this is the first run, initialize with the system prompt and the user request
    if not state.get("messages"):
        messages = [
            system_prompt,
            HumanMessage(content=f"Please parse and enrich the resume located at: {state['resume_path']}")
        ]
    else:
        messages = state["messages"]

    # Invoke the LLM
    response = llm.invoke(messages)
    
    # Check if the LLM outputted the final JSON (no more tool calls)
    enriched_json = ""
    if not response.tool_calls:
        try:
            # Clean up the markdown code block formatting if present
            clean_text = response.content.replace("```json", "").replace("```", "").strip()
            # Verify it's parseable
            json.loads(clean_text)
            enriched_json = clean_text
        except json.JSONDecodeError:
            pass # Handle gracefully in production

    return {"messages": [response], "enriched_json": enriched_json}

# ==========================================
# 4. CONDITIONAL ROUTING
# ==========================================
def should_continue(state: PortfolioState):
    """Determines if the Agent needs to call a tool or if it's finished."""
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END

# ==========================================
# 5. BUILD THE GRAPH
# ==========================================
workflow = StateGraph(PortfolioState)

workflow.add_node("parser", parser_node)
workflow.add_node("tools", tool_node)

workflow.add_edge(START, "parser")
workflow.add_conditional_edges("parser", should_continue, {"tools": "tools", END: END})
workflow.add_edge("tools", "parser")

parser_app = workflow.compile()

# ==========================================
# 6. TEST EXECUTION (Run this file directly)
# ==========================================
if __name__ == "__main__":
    initial_state = {
        "resume_path": "/uploads/mock_resume.pdf",
        "github_token": "mock_token",
        "vercel_token": "mock_token",
        "messages": []
    }
    
    print("🚀 Starting Agent 1 (Parser & Enrichment)...")
    
    # Stream the graph execution
    for output in parser_app.stream(initial_state, stream_mode="values"):
        last_msg = output["messages"][-1]
        last_msg.pretty_print()
    
    print("\n✅ Final Enriched JSON Output:")
    print(output.get("enriched_json"))