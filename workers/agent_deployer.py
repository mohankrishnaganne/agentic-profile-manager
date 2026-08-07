import base64
import requests

def deploy_node(state: dict) -> dict:
    """Agent 3: Automated CI/CD deployment to GitHub and Vercel APIs."""
    gh_token = state.get("github_token")
    vc_token = state.get("vercel_token")
    site_code = state.get("site_code")
    
    if not gh_token:
        return {"live_url": "Failed: No GitHub token provided."}

    headers = {
        "Authorization": f"token {gh_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    user_res = requests.get("https://api.github.com/user", headers=headers, timeout=10)
    if user_res.status_code != 200:
        return {"live_url": "Failed to authenticate with GitHub."}
    
    username = user_res.json()["login"]
    repo_name = "ai-portfolio"
    
    requests.post("https://api.github.com/user/repos", headers=headers, json={"name": repo_name, "private": False}, timeout=10)
    
    file_url = f"https://api.github.com/repos/{username}/{repo_name}/contents/index.html"
    file_res = requests.get(file_url, headers=headers, timeout=10)
    sha = file_res.json().get("sha") if file_res.status_code == 200 else None
    
    encoded_code = base64.b64encode(site_code.encode("utf-8")).decode("utf-8")
    push_payload = {"message": "Auto-deployed via Agentic Profile Manager 🤖", "content": encoded_code}
    if sha:
        push_payload["sha"] = sha
        
    push_res = requests.put(file_url, headers=headers, json=push_payload, timeout=10)
    github_url = f"https://github.com/{username}/{repo_name}"
    
    if push_res.status_code in [200, 201]:
        return {"live_url": github_url}
    return {"live_url": "Failed to push code to GitHub."}
