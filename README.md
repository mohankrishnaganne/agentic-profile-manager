# 🤖 Agentic Profile Manager 

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Stateful_Agents-orange)](https://python.langchain.com/docs/langgraph)
[![Flask](https://img.shields.io/badge/Flask-Web_Gateway-lightgrey)](https://flask.palletsprojects.com/)
[![Redis](https://img.shields.io/badge/Redis-Pub%2FSub_%26_Queue-red)](https://redis.io/)
[![Deployment](https://img.shields.io/badge/AWS-ECS_Fargate-FF9900?logo=amazonaws)](https://aws.amazon.com/ecs/)

An enterprise-grade, event-driven multi-agent orchestration platform. This system automates the ingestion of raw professional data, uses specialized Large Language Models (LLMs) to structure and design the data, and automatically deploys the generated artifacts to live hosting environments.

## 🌟 Core Value Proposition

Standard LLM API calls frequently result in server timeouts (504 Gateway Timeouts) during long-running generation tasks. **Agentic Profile Manager solves this by fully decoupling the web ingestion layer from the AI processing layer.** 

Using Redis as a message broker and Pub/Sub streaming, the architecture allows LangGraph workers to take as much time as they need to reason, interrogate tools, and generate code, while streaming real-time thought processes back to a highly responsive frontend UI.

## 🏗️ System Architecture

The application is structured as a scalable monorepo, separating concerns between HTTP handling and heavy LLM orchestration.

### 🧠 The Agents
1. **The Parser (Agent 1):** Extracts text from raw PDFs. It is heavily prompted to filter specific domains (e.g., emphasizing Data Engineering architectures while aggressively stripping out irrelevant test automation workflows) to ensure highly targeted profile generation.
2. **The Generator (Agent 2):** Takes the structured JSON payload and engineers a fully responsive, dark-themed Tailwind CSS single-page application.
3. **The Deployer (Agent 3):** Handles OAuth tokens to dynamically create GitHub repositories, commit source code, and trigger live Vercel deployments.

## 📂 Directory Structure

agentic-profile-manager/
├── .github/workflows/      # Automated CI/CD pipelines (AWS ECS)
├── shared/                 # Common configuration and file I/O utilities
├── web/                    # API Gateway (Flask, SSE streaming, OAuth)
│   └── templates/          # Frontend UI (HTML/Tailwind/Vanilla JS)
├── workers/                # Background processing (LangGraph, Redis Polling)
│   ├── graph.py            # Orchestrates the cyclic agent workflow
│   ├── state.py            # Defines the TypedDict for agent memory
│   └── agent_*.py          # Individual agent node logic
├── uploads/                # Ephemeral volume for incoming files
├── docker-compose.yml      # Local infrastructure orchestration
└── requirements.txt        # Shared Python dependencies

## ⚙️ Environment Variables

Create a `.env` file in the root directory. The application requires the following configurations to boot:

| Variable | Description | Required |
| :--- | :--- | :---: |
| `FLASK_SECRET_KEY` | Cryptographic key for securing session cookies. | **Yes** |
| `REDIS_HOST` | Hostname for the Redis broker (default: `localhost`). | **Yes** |
| `REDIS_PORT` | Port for the Redis broker (default: `6379`). | **Yes** |
| `GOOGLE_API_KEY` | Gemini API key for LLM orchestration. | **Yes** |
| `GITHUB_CLIENT_ID` | OAuth Client ID for GitHub integration. | Optional |
| `GITHUB_CLIENT_SECRET` | OAuth Client Secret for GitHub integration. | Optional |
| `VERCEL_CLIENT_ID` | OAuth Client ID for Vercel deployment. | Optional |
| `VERCEL_CLIENT_SECRET` | OAuth Client Secret for Vercel deployment. | Optional |

## 🚀 Local Development Setup

### Prerequisites
* Python 3.11+
* Docker (for running the local Redis broker)

### 1. Install Dependencies
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt

### 2. Start the Message Broker
docker run -d -p 6379:6379 --name local-redis redis

### 3. Start the Background Worker (Terminal 1)
The worker runs a continuous while-loop, blocking until a task appears in the Redis queue.
python -m workers.main

### 4. Start the API Gateway (Terminal 2)
The web server handles incoming requests and SSE (Server-Sent Events) log streaming.
python -m web.app

Navigate to `http://127.0.0.1:5000` to access the application.

## ☁️ Cloud Deployment (AWS ECS Fargate)

This repository includes a fully configured GitHub Actions workflow (`.github/workflows/aws-ecs-deploy.yml`) to deploy the architecture to AWS.

**How it works:**
1. Upon pushing to the `main` branch, the workflow triggers.
2. It builds two separate Docker images (`web` and `worker`).
3. Images are pushed to **Amazon ECR**.
4. The workflow updates the **Amazon ECS** task definitions and forces a rolling redeployment of the Fargate clusters.

## 🐛 Troubleshooting

* **ModuleNotFoundError: No module named 'shared'**
  * *Cause:* Python is treating the subdirectory as the root.
  * *Fix:* Always run the applications as modules from the project root using the `-m` flag (e.g., `python -m workers.main`).
* **Agents reusing old resume data on new uploads:**
  * *Cause:* LangGraph's `MemorySaver` requires unique `thread_id` parameters to isolate states.
  * *Fix:* Ensure the Flask API generates a new `uuid.uuid4()` for the `thread_id` on every POST request to `/upload-and-generate`, decoupling it from the persistent browser `session_id`.

---
*Built with LangGraph, Flask, and Redis.*
