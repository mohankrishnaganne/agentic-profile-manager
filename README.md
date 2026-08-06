# Agentic Profile Manager

An enterprise-grade, multi-agent orchestration platform designed to automate professional profile management and career workflows. 

Built with **LangGraph**, **Flask**, and **Redis**, this system leverages LLM agents to extract data, generate code, and interact with external APIs. The architecture strictly decouples the web API from the AI processing layer, utilizing a message queue and Pub/Sub streaming to ensure highly scalable, real-time Human-in-the-Loop (HITL) workflows without server timeouts.

## 🚀 Core Features

* **Multi-Agent Orchestration:** Utilizes LangGraph to manage stateful, cyclic interactions between specialized AI agents.
* **Intelligent Parsing (Agent 1):** Extracts professional experience from raw PDF documents, specifically filtering and optimizing data for Data Engineering and Analytics workflows, while stripping out irrelevant test automation points.
* **UI Generation (Agent 2):** Transforms the structured JSON data into a fully responsive, dark-themed HTML/Tailwind CSS web application.
* **Automated CI/CD (Agent 3):** Integrates seamlessly with the GitHub REST API and Vercel Deployment API for one-click repository creation and live web hosting.
* **Asynchronous Processing:** Uses Redis as a message broker to queue heavy LLM tasks, preventing web server exhaustion.
* **Real-Time Log Streaming:** Leverages Redis Pub/Sub to stream agent thought-processes and system logs directly to a frontend terminal UI via Server-Sent Events.

## 🏗️ Architecture & Project Structure

The codebase is structured as a monorepo, achieving Separation of Concerns (SoC) by physically isolating the web routing layer from the background LLM worker layer.

```text
agentic-profile-manager/
├── web/                        # The User Interface & API Gateway (Flask)
│   ├── app.py                  # API endpoints, file ingestion, and OAuth logic
│   └── templates/
│       └── index.html          # Interactive frontend with live terminal and iframe
├── workers/                    # The AI Brain & LangGraph Logic
│   ├── main.py                 # Background polling worker (Listens to Redis queue)
│   ├── graph.py                # The LangGraph StateGraph orchestrator
│   ├── state.py                # Defines the PortfolioState TypedDict
│   ├── agent_parser.py         # Agent 1: PDF extraction and tools
│   ├── agent_generator.py      # Agent 2: Tailwind UI generation
│   └── agent_deployer.py       # Agent 3: GitHub/Vercel API pushes
├── shared/                     # Shared utilities
│   ├── config.py               # Environment variable loading
│   └── file_handler.py         # Ephemeral PDF storage logic
├── uploads/                    # Temporary ephemeral storage (gitignored)
├── .env                        # API keys and secrets
├── requirements.txt            
└── README.md                   
⚙️ The Data Flow
Ingestion: The user uploads a resume via the Flask frontend. Flask saves the file, pushes a task to the Redis queue, and immediately returns a success response.

Execution: The background Python worker continuously polls Redis. It picks up the task and triggers the LangGraph orchestrator.

Streaming: As Agent 1 and Agent 2 execute their prompts and tool calls, the worker publishes live status messages to a Redis Pub/Sub channel.

Delivery: The Flask app subscribes to this channel and pushes the logs and the final generated HTML code to the browser, rendering it instantly in the UI's iframe.

Iteration: The user provides text feedback. Flask queues a REGENERATE task, the worker loops Agent 2 with the new instructions, and the UI updates dynamically.

🛠️ Getting Started (Local Development)
1. Clone the repository

Bash
git clone [https://github.com/yourusername/agentic-profile-manager.git](https://github.com/yourusername/agentic-profile-manager.git)
cd agentic-profile-manager
2. Install dependencies

Bash
pip install -r requirements.txt
3. Configure environment variables
Create a .env file in the root directory:

Code snippet
# Server & Redis Config
FLASK_SECRET_KEY=your_secure_flask_key
REDIS_HOST=localhost
REDIS_PORT=6379

# AI & API Keys
GOOGLE_API_KEY=your_gemini_api_key
GITHUB_CLIENT_ID=your_github_oauth_id
GITHUB_CLIENT_SECRET=your_github_oauth_secret
VERCEL_CLIENT_ID=your_vercel_oauth_id
VERCEL_CLIENT_SECRET=your_vercel_oauth_secret
4. Start the Local Infrastructure
To run this architecture locally, you will need three separate terminal windows:

Terminal 1 (Redis Broker):

Bash
docker run -d -p 6379:6379 --name local-redis redis
Terminal 2 (AI Worker):

Bash
python -m workers.main
Terminal 3 (Web Server):

Bash
python web/app.py
The web application will be accessible at http://127.0.0.1:5000.

🗺️ Roadmap
The architecture is highly modular and designed to scale. Future expansions include:

AWS Cloud Deployment: Porting the Redis queue to Amazon SQS and containerizing the Flask app and LangGraph workers on Amazon ECS (Fargate).

Persistent Checkpointing: Swapping out LangGraph's MemorySaver for a persistent PostgreSQL backend (langgraph-checkpoint-postgres) to allow cross-server HITL memory.

Browser Automation Agent: Adding a headless automation branch to automatically navigate job boards and submit applications based on the parsed data.