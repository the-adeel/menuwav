from fastapi import Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.types import Scope, Message
from starlette.responses import Response
import os

class StaticFilesWithCORS(StaticFiles):
    """StaticFiles with CORS headers"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Get allowed origins from environment variable
        allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
        self.allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
    
    async def __call__(self, scope: Scope, receive, send):
        if scope["type"] == "http":
            # Get origin from headers
            origin = None
            headers_list = scope.get("headers", [])
            for key, value in headers_list:
                if key.decode().lower() == b"origin":
                    origin = value.decode()
                    break
            
            # Wrap send to add CORS headers
            async def send_with_cors(message: Message):
                if message["type"] == "http.response.start":
                    # Get existing headers
                    existing_headers = list(message.get("headers", []))
                    
                    # Add CORS headers if origin is allowed (or allow all for now)
                    if origin in self.allowed_origins:
                        existing_headers.append((b"access-control-allow-origin", origin.encode()))
                    else:
                        # Allow all origins for static files
                        existing_headers.append((b"access-control-allow-origin", b"*"))
                    
                    existing_headers.append((b"access-control-allow-methods", b"GET, HEAD, OPTIONS"))
                    existing_headers.append((b"access-control-allow-headers", b"*"))
                    
                    message["headers"] = existing_headers
                await send(message)
            
            await super().__call__(scope, receive, send_with_cors)
        else:
            await super().__call__(scope, receive, send)

