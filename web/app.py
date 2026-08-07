import json
import os
import uuid
import base64
import requests
import redis
from flask import Flask, render_template, request, jsonify, redirect, session, Response

from shared.config import Config
from shared.file_handler import save_uploaded_file

app = Flask(__name__, template_folder="templates")
app.secret_key = Config.FLASK_SECRET_KEY

r = redis.Redis(host=Config.REDIS_HOST, port=Config.REDIS_PORT, db=0)

@app.route('/')
def index():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return render_template('index.html')

@app.route('/login/github')
def login_github():
    return redirect(f"https://github.com/login/oauth/authorize?client_id={Config.GITHUB_CLIENT_ID}&scope=repo")

@app.route('/callback/github')
def callback_github():
    code = request.args.get('code')
    res = requests.post(
        'https://github.com/login/oauth/access_token',
        data={'client_id': Config.GITHUB_CLIENT_ID, 'client_secret': Config.GITHUB_CLIENT_SECRET, 'code': code},
        headers={'Accept': 'application/json'},
        timeout=10
    )
    if res.status_code == 200:
        session['github_token'] = res.json().get('access_token')
        return redirect('/')
    return jsonify({"error": "GitHub Auth Failed"}), 400

@app.route('/login/vercel')
def login_vercel():
    return redirect("https://vercel.com/integrations/my-local-portfolio-app-123/new")

@app.route('/callback/vercel')
def callback_vercel():
    code = request.args.get('code')
    res = requests.post(
        'https://api.vercel.com/v2/oauth/access_token',
        data={
            'client_id': Config.VERCEL_CLIENT_ID,
            'client_secret': Config.VERCEL_CLIENT_SECRET,
            'code': code,
            'redirect_uri': 'http://127.0.0.1:5000/callback/vercel'
        },
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        timeout=10
    )
    if res.status_code == 200:
        session['vercel_token'] = res.json().get('access_token')
        return redirect('/')
    return jsonify({"error": "Vercel Auth Failed"}), 400

@app.route('/upload-and-generate', methods=['POST'])
def upload_and_generate():
    if 'resume' not in request.files or request.files['resume'].filename == '':
        return jsonify({"error": "No file uploaded"}), 400

    file_obj = request.files['resume']
    filepath = save_uploaded_file(file_obj)
    
    # job_id keeps the live logs streaming to your current browser window
    job_id = session.get('session_id', str(uuid.uuid4()))
    
    # NEW: Create a brand new memory thread ID for LangGraph on every upload
    thread_id = str(uuid.uuid4())

    task_payload = {
        "job_id": job_id,
        "thread_id": thread_id,  # <--- Add the new thread_id to the payload
        "action": "INITIAL_GENERATE",
        "filepath": filepath,
        "github_token": session.get('github_token', ''),
        "vercel_token": session.get('vercel_token', '')
    }
    r.rpush(Config.TASK_QUEUE, json.dumps(task_payload))
    return jsonify({"status": "queued", "job_id": job_id})

@app.route('/regenerate', methods=['POST'])
def regenerate():
    data = request.json or {}
    feedback = data.get('feedback', '')
    current_html = data.get('current_html', '')

    if not feedback or not current_html:
        return jsonify({"error": "Missing input data."}), 400

    job_id = session.get('session_id', str(uuid.uuid4()))
    task_payload = {
        "job_id": job_id,
        "action": "REGENERATE",
        "feedback": feedback,
        "current_html": current_html
    }
    r.rpush(Config.TASK_QUEUE, json.dumps(task_payload))
    return jsonify({"status": "queued", "job_id": job_id})

@app.route('/stream')
def stream():
    job_id = session.get('session_id')
    if not job_id:
        return jsonify({"error": "No session initialized"}), 400

    def event_stream():
        pubsub = r.pubsub()
        pubsub.subscribe(f"channel:{job_id}")
        for message in pubsub.listen():
            if message['type'] == 'message':
                yield f"data: {message['data'].decode('utf-8')}\n\n"

    return Response(event_stream(), mimetype="text/event-stream")

@app.route('/approve', methods=['POST'])
def approve_deployment():
    gh_token = session.get('github_token')
    vc_token = session.get('vercel_token')
    
    if not gh_token or not vc_token:
        return jsonify({"error": "Missing GitHub or Vercel authentication."}), 401
        
    data = request.json or {}
    site_code = data.get('html', '')
    if not site_code:
        return jsonify({"error": "No site HTML provided."}), 400

    gh_headers = {"Authorization": f"token {gh_token}", "Accept": "application/vnd.github.v3+json"}
    user_res = requests.get("https://api.github.com/user", headers=gh_headers, timeout=10)
    if user_res.status_code != 200:
        return jsonify({"error": "GitHub Auth invalid."}), 401

    username = user_res.json()["login"]
    repo_name = "ai-portfolio"
    requests.post("https://api.github.com/user/repos", headers=gh_headers, json={"name": repo_name, "private": False}, timeout=10)

    file_url = f"https://api.github.com/repos/{username}/{repo_name}/contents/index.html"
    file_res = requests.get(file_url, headers=gh_headers, timeout=10)
    sha = file_res.json().get("sha") if file_res.status_code == 200 else None

    encoded_code = base64.b64encode(site_code.encode("utf-8")).decode("utf-8")
    push_payload = {"message": "Deployed via Agentic Profile Manager 🤖", "content": encoded_code}
    if sha:
        push_payload["sha"] = sha

    push_res = requests.put(file_url, headers=gh_headers, json=push_payload, timeout=10)
    if push_res.status_code not in [200, 201]:
        return jsonify({"error": "Failed pushing to GitHub"}), 500

    github_url = f"https://github.com/{username}/{repo_name}"

    vercel_headers = {"Authorization": f"Bearer {vc_token}", "Content-Type": "application/json"}
    vercel_payload = {"name": repo_name, "files": [{"file": "index.html", "data": site_code}]}
    vercel_res = requests.post("https://api.vercel.com/v13/deployments", headers=vercel_headers, json=vercel_payload, timeout=10)

    if vercel_res.status_code == 200:
        live_url = "https://" + vercel_res.json().get("url", "")
        return jsonify({"status": "success", "vercel_url": live_url, "github_url": github_url})

    return jsonify({"error": f"Vercel Deployment error: {vercel_res.text}"}), 500

if __name__ == '__main__':
    app.run(debug=True, threaded=True, host="0.0.0.0", port=5000)
