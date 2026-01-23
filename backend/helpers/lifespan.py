# helpers/lifespan.py
from contextlib import asynccontextmanager
from tortoise import Tortoise
from helpers.tortoise_config import TORTOISE_ORM

@asynccontextmanager
async def lifespan():
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas(safe=True)  # Creates missing tables
    # Removed sync_model_columns() - conflicts with aerich migrations
    yield
    await Tortoise.close_connections()