import os
import queue
import threading
import requests
import json
import time
from typing import TypedDict, Annotated, List
import base64
import requests
import os
import PyPDF2
from werkzeug.utils import secure_filename
from flask import request, jsonify

import base64
import requests
from flask import session, request, jsonify
# --- ADD THESE IMPORTS AT THE TOP OF YOUR FILE ---
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from flask import Flask, request, redirect, session, Response, jsonify
from flask import redirect

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

import os
from werkzeug.utils import secure_filename
from flask import request, jsonify
import PyPDF2

from flask import render_template

# ==========================================
# 1. FLASK CONFIGURATION & STATE
# ==========================================
app = Flask(__name__)
app.secret_key = os.urandom(24) # Required for Flask sessions


GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID", "Ov23lisKykh4SDG4vaBS")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET", "c85d7e42a10cc38af7166127031cf94dceb301be")
VERCEL_CLIENT_ID = os.environ.get("VERCEL_CLIENT_ID", "oac_BzQZ6QPOGMPJ6ylHdbk0BW82")
VERCEL_CLIENT_SECRET = os.environ.get("VERCEL_CLIENT_SECRET", "cRIV3JsQSb8Bv3djRoyR41MB")

# MVP State Management for SSE
clients = {}

def get_client_queue(session_id):
    if session_id not in clients:
        clients[session_id] = queue.Queue()
    return clients[session_id]

def emit_event(session_id, event_type, data):
    q = get_client_queue(session_id)
    payload = json.dumps({"type": event_type, "data": data})
    q.put(f"data: {payload}\n\n")


# ==========================================
# 2. LANGGRAPH STATE & TOOLS (Agent 1)
# ==========================================
class PortfolioState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    resume_path: str
    github_token: str
    vercel_token: str
    enriched_json: str  
    site_code: str      
    live_url: str       

@tool
def read_file_mcp(file_path: str) -> str:
    """Reads the raw text from the uploaded PDF/DOCX resume."""
    return "Name: Alex Developer\nExperience: Software Engineer at Vercator (2022-2024).\nProjects: Built fast-cache (github.com/alex/fast-cache)"

@tool
def tavily_search_mcp(query: str) -> str:
    """Searches the web to find context on obscure company names."""
    print(f"[Tool: Tavily] Searching for: {query}")
    return "Vercator is an innovative UK startup specializing in 3D spatial data and point-cloud processing."

@tool
def github_stats_mcp(repo_path: str) -> str:
    """Fetches live star and fork counts from the GitHub API."""
    print(f"[Tool: GitHub] Fetching stats for: {repo_path}")
    return json.dumps({"stars": 1420, "forks": 180, "language": "C++"})

tools = [read_file_mcp, tavily_search_mcp, github_stats_mcp]
tool_node = ToolNode(tools)
# Agent 1: The Parser (Needs tool calling and low temperature for accuracy)
# gemini-1.5-pro is excellent for accurate data extraction and tool usage
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", 
    temperature=0.2
).bind_tools(tools)

# Agent 2: The Generator (Needs a bit more creativity for UI design)
# gemini-1.5-flash is extremely fast and handles large code outputs well
design_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", 
    temperature=0.4
)

# ==========================================
# 3. AGENT NODES
# ==========================================
def parser_node(state: PortfolioState):
    """Agent 1: Extracts data and calls tools."""
    messages = state.get("messages", [])
    new_messages = []
    
    # 1. If this is the very first run, set up the base conversation
    if not messages:
        sys_msg = SystemMessage(content="Extract resume data into JSON. Use tools to explain companies or fetch github stars. Output ONLY valid JSON at the end.")
        human_msg = HumanMessage(content=f"Parse resume at: {state['resume_path']}")
        
        # We add them to our local list to send to the LLM...
        messages = [sys_msg, human_msg]
        # ...AND we add them to new_messages so LangGraph saves them permanently!
        new_messages.extend([sys_msg, human_msg])

    # 2. Call Gemini
    response = llm.invoke(messages)
    new_messages.append(response)
    
    # 3. Parse final JSON if no tools are called
    enriched_json = ""
    if not response.tool_calls:
        try:
            clean_text = response.content.replace("```json", "").replace("```", "").strip()
            # Verify it is valid JSON
            json.loads(clean_text)
            enriched_json = clean_text
        except Exception as e:
            print(f"Warning: JSON parsing failed - {e}") 

    # 4. Return ALL new messages
    return {"messages": new_messages, "enriched_json": enriched_json}

def should_continue(state: PortfolioState):
    """Routes to tools or next agent."""
    if state["messages"][-1].tool_calls:
        return "tools"
    return "generator"

def generator_node(state: PortfolioState):
    """Agent 2: Generates Tailwind HTML."""
    system_prompt = SystemMessage(content="""
    You are an expert Frontend Developer. Take the provided JSON and generate a single-page HTML portfolio using Tailwind CSS via CDN.
    Output ONLY raw HTML. No markdown wrappers.
    """)
    human_message = HumanMessage(content=f"Generate HTML for:\n{state['enriched_json']}")
    
    response = design_llm.invoke([system_prompt, human_message])
    raw_html = response.content.replace("```html", "").replace("```", "").strip()
        
    return {"site_code": raw_html}

import base64

def deploy_node(state: PortfolioState):
    """Agent 3: Pushes the generated HTML to the user's GitHub account."""
    
    gh_token = state.get("github_token")
    site_code = state.get("site_code")
    
    if not gh_token or gh_token == "mock_gh_token":
        print("❌ Deployment failed: No valid GitHub token.")
        return {"live_url": "Failed: No GitHub token connected."}

    headers = {
        "Authorization": f"token {gh_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # 1. Get the authenticated user's GitHub username
    user_res = requests.get("https://api.github.com/user", headers=headers)
    if user_res.status_code != 200:
        return {"live_url": "Failed to authenticate with GitHub."}
    username = user_res.json()["login"]
    
    repo_name = "ai-portfolio"
    
    # 2. Create the repository (fails gracefully if it already exists)
    repo_payload = {"name": repo_name, "description": "Auto-generated AI Portfolio", "private": False}
    requests.post("https://api.github.com/user/repos", headers=headers, json=repo_payload)
    
    # 3. Push the index.html file to the repository
    file_url = f"https://api.github.com/repos/{username}/{repo_name}/contents/index.html"
    
    # Check if file already exists to get its SHA (required for updating existing files)
    file_res = requests.get(file_url, headers=headers)
    sha = file_res.json().get("sha") if file_res.status_code == 200 else None
    
    # GitHub requires file content to be Base64 encoded
    encoded_code = base64.b64encode(site_code.encode("utf-8")).decode("utf-8")
    
    push_payload = {
        "message": "Auto-deployed via AI Portfolio Builder 🤖",
        "content": encoded_code
    }
    if sha:
        push_payload["sha"] = sha
        
    push_res = requests.put(file_url, headers=headers, json=push_payload)
    
    if push_res.status_code in [200, 201]:
        github_url = f"https://github.com/{username}/{repo_name}"
        print(f"✅ Successfully deployed to {github_url}")
        
        # For now, return the GitHub URL. We will add the Vercel trigger next!
        return {"live_url": github_url}
    else:
        print(f"❌ Failed to push file: {push_res.json()}")
        return {"live_url": "Failed to push code to GitHub."}

# ==========================================
# 4. BUILD THE GRAPH ORCHESTRATOR
# ==========================================
workflow = StateGraph(PortfolioState)
workflow.add_node("parser", parser_node)
workflow.add_node("tools", tool_node)
workflow.add_node("generator", generator_node)
workflow.add_node("deployer", deploy_node)

workflow.add_edge(START, "parser")
workflow.add_conditional_edges("parser", should_continue, {"tools": "tools", "generator": "generator"})
workflow.add_edge("tools", "parser")
workflow.add_edge("generator", "deployer")
workflow.add_edge("deployer", END)

# Add Durable Memory & HITL Breakpoint
memory = MemorySaver()
portfolio_app = workflow.compile(
    checkpointer=memory, 
    interrupt_before=["deployer"]
)

# ==========================================
# 5. FLASK ROUTES & OAUTH
# ==========================================

@app.route('/')
def index():
    print("🔑 Current GitHub Token in Session:", session.get('github_token'))
    return render_template('index.html')

@app.route('/login/github')
def login_github():
    return redirect(f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&scope=repo")

@app.route('/callback/github')
def callback_github():
    code = request.args.get('code')
    res = requests.post(
        'https://github.com/login/oauth/access_token',
        data={'client_id': GITHUB_CLIENT_ID, 'client_secret': GITHUB_CLIENT_SECRET, 'code': code},
        headers={'Accept': 'application/json'}
    )
    if res.status_code == 200:
        session['github_token'] = res.json().get('access_token')
        return redirect('/')
    return jsonify({"error": "GitHub Auth Failed"}), 400


@app.route('/login/vercel')
def login_vercel():
    # Change it to match your actual Vercel integration slug!
    return redirect("https://vercel.com/integrations/my-local-portfolio-app-123/new?state=...")

@app.route('/callback/vercel')
def callback_vercel():
    code = request.args.get('code')
    res = requests.post(
        'https://api.vercel.com/v2/oauth/access_token',
        data={
            'client_id': VERCEL_CLIENT_ID, 
            'client_secret': VERCEL_CLIENT_SECRET, 
            'code': code,
            'redirect_uri': 'http://127.0.0.1:5000/callback/vercel' # <-- This is the required missing parameter!
        },
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    
    if res.status_code == 200:
        session['vercel_token'] = res.json().get('access_token')
        return redirect('/') # Bounces you back to the UI!
        
    # Helpful debugging: prints the exact Vercel error to your terminal if it fails again
    print("Vercel Auth Error:", res.text) 
    return jsonify({"error": "Vercel Auth Failed"}), 400

# Add these two lines to configure the directory before the route runs!
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/upload-and-generate', methods=['POST'])
def upload_and_generate():
    try:
        # 1. File Handling
        if 'resume' not in request.files or request.files['resume'].filename == '':
            return jsonify({"error": "No file uploaded"}), 400
            
        file = request.files['resume']
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # 2. Extract Text from PDF
        resume_text = ""
        with open(filepath, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                resume_text += page.extract_text()
                
        # 3. Initialize the REAL Gemini 1.5 Pro AI
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2)
        
        # 4. The System Prompt (This tells the AI exactly how to style the output)
        parser_system_prompt = """
        You are an expert Frontend Developer and Technical Resume Parser. Analyze the provided resume text and generate a single-page HTML portfolio using Tailwind CSS via CDN.
        
        CRITICAL CONTENT INSTRUCTIONS:
        - When extracting professional experience for the roles at Resideo and Niar, you must strictly remove all mentions of quality assurance and test automation tools.
        - Focus entirely on tasks, achievements, and workflows related to Data Engineering and Data Analytics.
        - Highlight technical proficiencies including Apache Spark, AWS, Snowflake, Pandas, and database architectures.
        - Ensure the education section is prominently captured in the header.
        
        CRITICAL FORMATTING INSTRUCTIONS:
        - Output ONLY raw HTML. 
        - Do not include markdown wrappers (like ```html). 
        - Ensure it is a complete, responsive, and beautiful dark-themed Tailwind UI.
        """
        
        # 5. Send the extracted text to Gemini
        print("🧠 Sending resume data to Gemini 1.5 Pro...")
        messages = [
            SystemMessage(content=parser_system_prompt),
            HumanMessage(content=f"Generate the HTML portfolio for this resume:\n\n{resume_text}")
        ]
        
        # This is where the magic happens!
        response = llm.invoke(messages)
        
        # 6. Clean up the AI output (stripping accidental markdown blocks)
        generated_html = response.content.replace("```html", "").replace("```", "").strip()
        
        return jsonify({
            "status": "success",
            "html": generated_html
        })
        
    except Exception as e:
        print(f"Error during generation: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/regenerate', methods=['POST'])
def regenerate_portfolio():
    try:
        data = request.json
        feedback = data.get('feedback', '')
        current_html = data.get('current_html', '')

        if not feedback or not current_html:
            return jsonify({"error": "Missing feedback or current HTML."}), 400

        # We can use a slightly higher temperature here for creative design changes
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.4)

        # The System Prompt for Iteration
        system_prompt = """
        You are an expert Frontend Developer modifying a Tailwind CSS portfolio based on user feedback.
        
        CRITICAL INSTRUCTIONS:
        1. Apply the user's specific design/layout feedback to the provided HTML.
        2. DO NOT alter, summarize, or remove the underlying professional experience text or resume data unless the user explicitly asks you to.
        3. Output ONLY raw HTML. Do not include markdown wrappers (like ```html).
        4. Ensure the output remains a complete, valid, and responsive HTML document using Tailwind CDN.
        """

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"CURRENT HTML:\n{current_html}\n\nUSER FEEDBACK:\n{feedback}\n\nPlease regenerate the HTML incorporating this exact feedback.")
        ]

        print(f"✨ Iterating on design via Gemini... Feedback: '{feedback}'")
        response = llm.invoke(messages)
        
        # Clean up the output
        generated_html = response.content.replace("```html", "").replace("```", "").strip()

        return jsonify({
            "status": "success",
            "html": generated_html
        })

    except Exception as e:
        print(f"Error during regeneration: {e}")
        return jsonify({"error": str(e)}), 500
    

# ==========================================
# 6. SSE STREAMING & WORKFLOW TRIGGERS
# ==========================================
@app.route('/stream')
def stream():
    if not session.get('session_id'):
        session['session_id'] = os.urandom(8).hex()
        
    q = get_client_queue(session['session_id'])

    def event_generator():
        while True:
            try:
                yield q.get(timeout=30)
            except queue.Empty:
                yield ": keep-alive\n\n"

    return Response(event_generator(), mimetype="text/event-stream")



@app.route('/approve', methods=['POST'])
def approve_deployment():
    try:
        # 1. Verify Authentication & Data
        gh_token = session.get('github_token')
        vc_token = session.get('vercel_token')
        
        if not gh_token or not vc_token:
            return jsonify({"error": "Missing GitHub or Vercel token. Please connect both."}), 401
            
        data = request.json
        site_code = data.get('html', '')
        if not site_code:
            return jsonify({"error": "No HTML code provided for deployment."}), 400

        # ==========================================
        # STEP A: PUSH SOURCE CODE TO GITHUB
        # ==========================================
        print("🐙 Pushing code to GitHub...")
        gh_headers = {
            "Authorization": f"token {gh_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        user_res = requests.get("https://api.github.com/user", headers=gh_headers)
        if user_res.status_code != 200:
            return jsonify({"error": "Failed to authenticate with GitHub."}), 401
        username = user_res.json()["login"]

        repo_name = "ai-portfolio"
        repo_payload = {"name": repo_name, "description": "Auto-generated AI Portfolio", "private": False}
        requests.post("https://api.github.com/user/repos", headers=gh_headers, json=repo_payload)

        file_url = f"https://api.github.com/repos/{username}/{repo_name}/contents/index.html"
        file_res = requests.get(file_url, headers=gh_headers)
        sha = file_res.json().get("sha") if file_res.status_code == 200 else None

        encoded_code = base64.b64encode(site_code.encode("utf-8")).decode("utf-8")
        push_payload = {
            "message": "Auto-deployed via AI Portfolio Builder 🤖",
            "content": encoded_code
        }
        if sha:
            push_payload["sha"] = sha

        push_res = requests.put(file_url, headers=gh_headers, json=push_payload)
        
        if push_res.status_code not in [200, 201]:
            return jsonify({"error": f"GitHub push failed: {push_res.text}"}), 500
            
        github_url = f"https://github.com/{username}/{repo_name}"
        print(f"✅ Successfully deployed to GitHub: {github_url}")

        # ==========================================
        # STEP B: DEPLOY LIVE APP TO VERCEL
        # ==========================================
        print("▲ Deploying live site to Vercel...")
        
        # Vercel uses 'Bearer' instead of 'token' for authentication
        vercel_headers = {
            "Authorization": f"Bearer {vc_token}",
            "Content-Type": "application/json"
        }
        
        # We send the raw HTML directly to Vercel's deployment engine
        vercel_payload = {
            "name": repo_name,
            "files": [
                {
                    "file": "index.html",
                    "data": site_code
                }
            ],
            "projectSettings": {
                "framework": None # Native HTML/Tailwind doesn't need a framework
            }
        }
        
        vercel_res = requests.post("https://api.vercel.com/v13/deployments", headers=vercel_headers, json=vercel_payload)
        
        if vercel_res.status_code == 200:
            vercel_data = vercel_res.json()
            # Vercel returns the URL without the protocol, so we add https://
            live_url = "https://" + vercel_data.get("url") 
            print(f"✅ Successfully deployed to Vercel: {live_url}")
            
            return jsonify({
                "status": "success",
                "message": "Deployment triggered successfully!",
                "vercel_url": live_url,
                "github_url": github_url
            })
        else:
            return jsonify({"error": f"Vercel deployment failed: {vercel_res.text}"}), 500

    except Exception as e:
        print(f"Error during deployment: {e}")
        return jsonify({"error": str(e)}), 500
    
# ==========================================
# 7. BACKGROUND WORKERS
# ==========================================
def run_langgraph_workflow(session_id: str, gh_token: str, vc_token: str):
    config = {"configurable": {"thread_id": session_id}}
    initial_state = {
        "resume_path": "mock_resume.pdf", 
        "github_token": gh_token,
        "vercel_token": vc_token,
        "messages": []
    }

    emit_event(session_id, "status", "Starting Portfolio Generation...")

    for event in portfolio_app.stream(initial_state, config=config):
        if "parser" in event:
            emit_event(session_id, "log", "Agent 1 extracted resume data.")
        elif "tools" in event:
            emit_event(session_id, "log", "Agent 1 fetched external context via MCP.")
        elif "generator" in event:
            emit_event(session_id, "log", "Agent 2 generated the HTML code.")
            
    current_state = portfolio_app.get_state(config)
    
    if "deployer" in current_state.next:
        generated_html = current_state.values.get("site_code", "")
        emit_event(session_id, "hitl_breakpoint", {
            "message": "Site generated! Awaiting your approval.",
            "code": generated_html
        })

def resume_langgraph_workflow(session_id: str):
    """Picks up where the graph paused and triggers Agent 3 (Deployer)."""
    config = {"configurable": {"thread_id": session_id}}
    emit_event(session_id, "status", "Deploying site...")
    
    # Passing None to .stream() resumes execution from the breakpoint
    for event in portfolio_app.stream(None, config=config):
        if "deployer" in event:
            url = event["deployer"].get("live_url")
            emit_event(session_id, "log", f"Agent 3 successfully deployed: {url}")
            emit_event(session_id, "complete", {"url": url})

if __name__ == '__main__':
    app.run(debug=True, threaded=True, port=5000)