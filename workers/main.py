import json
import time
import redis
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from shared.config import Config
from shared.file_handler import extract_text_from_pdf
from workers.graph import portfolio_app

r = redis.Redis(host=Config.REDIS_HOST, port=Config.REDIS_PORT, db=0)

def emit_event(job_id: str, event_type: str, data: dict):
    payload = json.dumps({"job_id": job_id, "type": event_type, "data": data})
    r.publish(f"channel:{job_id}", payload)

def process_job(job_data: dict):
    job_id = job_data.get("job_id")
    
    # NEW: Extract the unique thread_id (fallback to job_id if not present)
    thread_id = job_data.get("thread_id", job_id) 
    
    action = job_data.get("action")
    
    emit_event(job_id, "log", {"message": f"Worker accepted task [{action}]"})

    try:
        if action == "INITIAL_GENERATE":
            filepath = job_data.get("filepath")
            resume_text = extract_text_from_pdf(filepath)
            
            # UPDATE: Use the unique thread_id to force LangGraph to start with a blank memory
            config = {"configurable": {"thread_id": thread_id}} 
            
            initial_state = {
                "resume_path": filepath,
                "resume_text": resume_text,
                "github_token": job_data.get("github_token", ""),
                "vercel_token": job_data.get("vercel_token", ""),
                "messages": []
            }

            for event in portfolio_app.stream(initial_state, config=config):
                if "parser" in event:
                    emit_event(job_id, "log", {"message": "Agent 1: Parsed resume & focused Data Engineering skills."})
                elif "generator" in event:
                    emit_event(job_id, "log", {"message": "Agent 2: Generated dark-themed Tailwind CSS UI."})

            final_state = portfolio_app.get_state(config)
            site_code = final_state.values.get("site_code", "")
            
            emit_event(job_id, "complete", {"html": site_code})

        elif action == "REGENERATE":
            feedback = job_data.get("feedback")
            current_html = job_data.get("current_html")
            
            emit_event(job_id, "log", {"message": f"Agent 2 refining design based on feedback: '{feedback}'"})
            
            design_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.4, google_api_key=Config.GOOGLE_API_KEY)
            sys_msg = SystemMessage(content="You are an expert Frontend Developer. Modify the HTML per feedback. Output ONLY raw HTML.")
            human_msg = HumanMessage(content=f"CURRENT HTML:\n{current_html}\n\nFEEDBACK:\n{feedback}")
            
            res = design_llm.invoke([sys_msg, human_msg])
            updated_html = res.content.replace("```html", "").replace("```", "").strip()
            
            emit_event(job_id, "complete", {"html": updated_html})

    except Exception as e:
        emit_event(job_id, "error", {"message": str(e)})

def start_worker():
    print(f"🚀 Worker process polling Redis queue '{Config.TASK_QUEUE}' on {Config.REDIS_HOST}:{Config.REDIS_PORT}...")
    while True:
        try:
            _, raw_payload = r.blpop(Config.TASK_QUEUE)
            job_data = json.loads(raw_payload.decode('utf-8'))
            process_job(job_data)
        except KeyboardInterrupt:
            print("\n🛑 Worker interrupted. Shutting down.")
            break
        except Exception as e:
            print(f"❌ Worker loop exception: {e}")
            time.sleep(1)

if __name__ == "__main__":
    start_worker()
