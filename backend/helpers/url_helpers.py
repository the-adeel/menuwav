import os
from dotenv import load_dotenv

load_dotenv()

def get_frontend_url():
    """
    Get the frontend URL from environment variables.
    Falls back to extracting from ALLOWED_ORIGINS if FRONTEND_URL is not set.
    Returns the first non-localhost origin from ALLOWED_ORIGINS if available.
    """
    base_url = os.getenv("FRONTEND_URL")
    
    # If FRONTEND_URL is not set, try to extract from ALLOWED_ORIGINS
    if not base_url:
        allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
        allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
        if allowed_origins:
            # Use the first origin that's not localhost (prefer production URL)
            # If all are localhost, use the first one
            base_url = next((origin for origin in allowed_origins if "localhost" not in origin and "127.0.0.1" not in origin), allowed_origins[0])
        else:
            base_url = "http://localhost:5173"
    
    # Log warning if using localhost in production (heuristic: check if not explicitly set)
    if ("localhost" in base_url or "127.0.0.1" in base_url) and not os.getenv("FRONTEND_URL"):
        print(f"WARNING: Using localhost URL for redirects: {base_url}. Set FRONTEND_URL environment variable for production.")
    
    return base_url

