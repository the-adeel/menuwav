from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from controllers.auth_controller import router as auth_router
from controllers.restaurant_controller import router as restaurant_router
from controllers.menu_controller import router as menu_router
from controllers.qr_controller import router as qr_router
from controllers.order_controller import router as order_router
from helpers.lifespan import lifespan

@asynccontextmanager
async def app_lifespan(app: FastAPI):
    async with lifespan():
        yield

app = FastAPI(lifespan=app_lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth")
app.include_router(restaurant_router, prefix="/restaurants")
app.include_router(menu_router, prefix="/menus")
app.include_router(qr_router, prefix="/restaurants")
app.include_router(order_router, prefix="")