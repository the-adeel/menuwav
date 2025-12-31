from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

from controllers.auth_controller import router as auth_router
from controllers.restaurant_controller import router as restaurant_router
from controllers.menu_controller import router as menu_router
from controllers.qr_controller import router as qr_router
from controllers.order_controller import router as order_router
from controllers.file_controller import router as file_router
from helpers.lifespan import lifespan

@asynccontextmanager
async def app_lifespan(app: FastAPI):
    async with lifespan():
        yield

app = FastAPI(lifespan=app_lifespan)

# Add CORS middleware
# Get allowed origins from environment variable, default to localhost for development
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Frontend URLs from environment variable
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth")
app.include_router(restaurant_router, prefix="/restaurants")
app.include_router(menu_router, prefix="/menus")
app.include_router(qr_router, prefix="/restaurants")
app.include_router(order_router, prefix="")
app.include_router(file_router, prefix="/files")

# Mount static files for uploads
if os.path.exists("uploads"):
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")