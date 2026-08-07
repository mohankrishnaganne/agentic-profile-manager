from typing import TypedDict, Annotated, List
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class PortfolioState(TypedDict):
    """Shared state dictionary passed across all LangGraph nodes."""
    messages: Annotated[List[BaseMessage], add_messages]
    resume_path: str
    resume_text: str
    github_token: str
    vercel_token: str
    enriched_json: str  
    site_code: str      
    live_url: str       
