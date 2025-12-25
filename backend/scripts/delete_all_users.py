# delete_all_users.py
# This script deletes all users from the database
import asyncio
import sys
import os

script_dir = os.path.dirname(os.path.realpath(__file__))
backend_dir = os.path.dirname(script_dir)  # Go up one level to backend/
sys.path.insert(0, backend_dir)

from dotenv import load_dotenv

from models.user import User
from tortoise import Tortoise
from helpers.tortoise_config import TORTOISE_ORM

load_dotenv()

async def init():
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas(safe=True)

    # Get all users
    users = await User.all()
    count = len(users)
    
    if count == 0:
        print("No users found in the database.")
    else:
        # Delete all users
        for user in users:
            print(f"Deleting user: {user.username} (ID: {user.id}, Role: {user.role.value})")
            await user.delete()
        
        print(f"\nDeleted {count} user(s) successfully!")

    await Tortoise.close_connections()

asyncio.run(init())

