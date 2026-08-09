import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Centralized Environment and Application Configuration."""
    FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "default-dev-secret-key-change-me")
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    TASK_QUEUE = "task_queue"
    
    # OAuth Credentials
    GH_CLIENT_ID = os.getenv("GH_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
    VERCEL_CLIENT_ID = os.getenv("VERCEL_CLIENT_ID", "")
    VERCEL_CLIENT_SECRET = os.getenv("VERCEL_CLIENT_SECRET", "")
    
    # AI Credentials
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    
    # File Storage
    UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), "../uploads"))
