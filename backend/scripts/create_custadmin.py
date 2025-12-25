# create_customer.py
import asyncio
import sys
import os

# Add the current directory (backend root) to Python path
script_dir = os.path.dirname(os.path.realpath(__file__))
backend_dir = os.path.dirname(script_dir)  # Go up one level to backend/
sys.path.insert(0, backend_dir)
import bcrypt
from dotenv import load_dotenv

from models.user import User, Role
from tortoise import Tortoise
from helpers.tortoise_config import TORTOISE_ORM

load_dotenv()

async def init():
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas(safe=True)

    username = "customer"
    password = "cust123"

    if await User.exists(username=username):
        print(f"Customer '{username}' already exists!")
    else:
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        await User.create(username=username, password=hashed, role=Role.CUSTOMER)
        print(f"Customer created -> username: {username} | password: {password}")

    await Tortoise.close_connections()

asyncio.run(init())