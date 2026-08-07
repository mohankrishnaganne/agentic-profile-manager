from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from shared.config import Config

design_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", 
    temperature=0.4,
    google_api_key=Config.GOOGLE_API_KEY
)

def generator_node(state: dict) -> dict:
    """Agent 2: Converts structured JSON into responsive Tailwind CSS HTML."""
    system_prompt = SystemMessage(content="""
    You are an expert Frontend Developer. Take the provided JSON and generate a single-page HTML portfolio using Tailwind CSS via CDN.
    Design a dark-themed UI highlighting Data Engineering experience and education.
    Output ONLY raw HTML. No markdown wrappers.
    """)
    human_message = HumanMessage(content=f"Generate HTML for:\n{state.get('enriched_json', '')}")
    
    response = design_llm.invoke([system_prompt, human_message])
    raw_html = response.content.replace("```html", "").replace("```", "").strip()
    return {"site_code": raw_html}
