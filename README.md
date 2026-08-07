$readmeContent = @'
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

```mermaid
graph TD
    User[User / Browser] -->|1. Uploads PDF| API[Flask API Gateway]
    API -->|2. Enqueues Task| Queue[(Redis Task Queue)]
    API <-->|5. SSE Stream| PubSub[(Redis Pub/Sub)]
    
    Worker[LangGraph Python Worker] -->|3. Polls for Tasks| Queue
    Worker -->|4. Streams Logs| PubSub
    
    subgraph Agentic Pipeline
        Worker --> A1[Agent 1: Data Extraction]
        A1 --> A2[Agent 2: Tailwind Generation]
        A2 --> A3[Agent 3: GitHub/Vercel CI/CD]
    end
🧠 The AgentsThe Parser (Agent 1): Extracts text from raw PDFs. It is heavily prompted to filter specific domains (e.g., emphasizing Data Engineering architectures while aggressively stripping out irrelevant test automation workflows) to ensure highly targeted profile generation.The Generator (Agent 2): Takes the structured JSON payload and engineers a fully responsive, dark-themed Tailwind CSS single-page application.The Deployer (Agent 3): Handles OAuth tokens to dynamically create GitHub repositories, commit source code, and trigger live Vercel deployments.📂 Directory StructurePlaintextagentic-profile-manager/
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
⚙️ Environment VariablesCreate a .env file in the root directory. The application requires the following configurations to boot:VariableDescriptionRequiredFLASK_SECRET_KEYCryptographic key for securing session cookies.YesREDIS_HOSTHostname for the Redis broker (default: localhost).YesREDIS_PORTPort for the Redis broker (default: 6379).YesGOOGLE_API_KEYGemini API key for LLM orchestration.YesGITHUB_CLIENT_IDOAuth Client ID for GitHub integration.OptionalGITHUB_CLIENT_SECRETOAuth Client Secret for GitHub integration.OptionalVERCEL_CLIENT_IDOAuth Client ID for Vercel deployment.OptionalVERCEL_CLIENT_SECRETOAuth Client Secret for Vercel deployment.Optional🚀 Local Development SetupPrerequisitesPython 3.11+Docker (for running the local Redis broker)1. Install DependenciesBashpython -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
2. Start the Message BrokerBashdocker run -d -p 6379:6379 --name local-redis redis
3. Start the Background Worker (Terminal 1)The worker runs a continuous while-loop, blocking until a task appears in the Redis queue.Bashpython -m workers.main
4. Start the API Gateway (Terminal 2)The web server handles incoming requests and SSE (Server-Sent Events) log streaming.Bashpython -m web.app
Navigate to http://127.0.0.1:5000 to access the application.☁️ Cloud Deployment (AWS ECS Fargate)This repository includes a fully configured GitHub Actions workflow (.github/workflows/aws-ecs-deploy.yml) to deploy the architecture to AWS.How it works:Upon pushing to the main branch, the workflow triggers.It builds two separate Docker images (web and worker).Images are pushed to Amazon ECR.The workflow updates the Amazon ECS task definitions and forces a rolling redeployment of the Fargate clusters.🐛 TroubleshootingModuleNotFoundError: No module named 'shared'Cause: Python is treating the subdirectory as the root.Fix: Always run the applications as modules from the project root using the -m flag (e.g., python -m workers.main).Agents reusing old resume data on new uploads:Cause: LangGraph's MemorySaver requires unique thread_id parameters to isolate states.Fix: Ensure the Flask API generates a new uuid.uuid4() for the thread_id on every POST request to /upload-and-generate, decoupling it from the persistent browser session_id.Built with LangGraph, Flask, and Redis.'@
