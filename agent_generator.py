import json
from typing import TypedDict, Annotated, List
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# ==========================================
# 1. STATE DEFINITION (Must match Agent 1)
# ==========================================
class PortfolioState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    resume_path: str
    github_token: str
    vercel_token: str
    enriched_json: str  
    site_code: str      # Agent 2 will populate this
    live_url: str       

# ==========================================
# 2. DEFINE THE GENERATOR AGENT NODE
# ==========================================
# We use a slightly more creative/higher temperature model here for design
llm = ChatOpenAI(model="gpt-4o", temperature=0.4)

def generator_node(state: PortfolioState):
    """Agent 2: Takes enriched JSON and writes a Tailwind HTML template."""
    
    # Safety check in case JSON is missing
    if not state.get("enriched_json"):
        raise ValueError("Missing enriched_json in state. Agent 1 must run first.")

    system_prompt = SystemMessage(content="""
    You are an expert Frontend Developer and UI/UX Designer. 
    Your task is to take the provided JSON portfolio data and generate a stunning, modern, fully responsive single-page HTML website.
    
    Technical Requirements:
    1. Use Tailwind CSS via CDN (<script src="https://cdn.tailwindcss.com"></script>).
    2. Design a sleek, dark-mode aesthetic (e.g., bg-slate-900, text-slate-300).
    3. Include 3 distinct sections: 
       - Hero (Name and brief intro)
       - Experience (Use the enriched company descriptions)
       - Projects (Display GitHub star/fork counts prominently using Tailwind badges)
    4. Ensure the layout is responsive (mobile-first).
    
    Output Format:
    Output ONLY the raw HTML code. Do not include markdown wrappers (like ```html), explanations, or comments. Just the raw, valid HTML string.
    """)

    human_message = HumanMessage(
        content=f"Please generate the Tailwind HTML portfolio for the following data:\n\n{state['enriched_json']}"
    )

    print("🎨 Agent 2 is designing and generating the codebase...")
    response = llm.invoke([system_prompt, human_message])
    
    # Clean up the output in case the LLM ignored the instruction about markdown wrappers
    raw_html = response.content.strip()
    if raw_html.startswith("```html"):
        raw_html = raw_html[7:]
    if raw_html.endswith("```"):
        raw_html = raw_html[:-3]
        
    return {"site_code": raw_html.strip()}

# ==========================================
# 3. BUILD THE GRAPH (For standalone testing)
# ==========================================
workflow = StateGraph(PortfolioState)
workflow.add_node("generator", generator_node)
workflow.add_edge(START, "generator")
workflow.add_edge("generator", END)

generator_app = workflow.compile()

# ==========================================
# 4. TEST EXECUTION (Run this file directly)
# ==========================================
if __name__ == "__main__":
    # Mock data that Agent 1 would have produced
    mock_enriched_json = json.dumps({
        "name": "Alex Developer",
        "experience": [
            {
                "role": "Software Engineer",
                "company": "Vercator",
                "duration": "2022-2024",
                "description": "Vercator is an innovative UK startup specializing in 3D spatial data and point-cloud processing.",
                "bullets": ["Implemented Practical Byzantine Fault Tolerance (PBFT), a high-performance distributed consensus algorithm."]
            }
        ],
        "projects": [
            {
                "name": "fast-cache",
                "description": "Built a high-performance caching library.",
                "url": "[github.com/alex/fast-cache](https://github.com/alex/fast-cache)",
                "language": "C++",
                "stars": 1420,
                "forks": 180
            }
        ]
    })

    initial_state = {
        "resume_path": "",
        "github_token": "",
        "vercel_token": "",
        "messages": [],
        "enriched_json": mock_enriched_json,
        "site_code": "",
        "live_url": ""
    }
    
    print("🚀 Starting Agent 2 (Site Generator)...")
    
    final_state = generator_app.invoke(initial_state)
    
    print("\n✅ Final HTML Output Generated:\n")
    print(final_state["site_code"][:500] + "\n\n... [TRUNCATED] ...\n")
    
    # Optional: Save to a file to open in your browser
    with open("test_portfolio.html", "w") as f:
        f.write(final_state["site_code"])
    print("💾 Saved to test_portfolio.html! Open this file in your browser to see the result.")