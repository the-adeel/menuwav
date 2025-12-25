# create_superadmin.py
import asyncio
import sys
import os

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

    username = "superadmin"
    password = "super123"  # Change if you want

    if await User.exists(username=username):
        print(f"Superadmin '{username}' already exists!")
        existing_user = await User.get(username=username)
        print(f"Existing superadmin credentials -> username: {username} | password: {password}")
    else:
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        # Create without email/phone in case migrations haven't been run yet
        try:
            await User.create(username=username, password=hashed, role=Role.SUPERADMIN)
            print(f"Superadmin created -> username: {username} | password: {password}")
        except Exception as e:
            # If email/phone columns don't exist, try without them
            if "email" in str(e) or "phone" in str(e):
                # This shouldn't happen with the current model, but just in case
                print(f"Error: {e}")
                print("Please run migrations first: aerich migrate && aerich upgrade")
            else:
                raise

    await Tortoise.close_connections()

asyncio.run(init())