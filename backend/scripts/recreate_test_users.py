# recreate_test_users.py
# This script deletes and recreates all test users with proper bcrypt hashing
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

    # Test users to create
    test_users = [
        {"username": "superadmin", "password": "super123", "role": Role.SUPERADMIN},
        {"username": "restadmin", "password": "rest123", "role": Role.RESTAURANT_ADMIN},
        {"username": "customer", "password": "cust123", "role": Role.CUSTOMER},
    ]

    for user_data in test_users:
        username = user_data["username"]
        password = user_data["password"]
        role = user_data["role"]
        
        # Delete existing user if it exists
        existing_user = await User.get_or_none(username=username)
        if existing_user:
            await existing_user.delete()
            print(f"Deleted existing user '{username}'")
        
        # Create new user with proper bcrypt hash
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        await User.create(username=username, password=hashed, role=role)
        print(f"Created user -> username: {username} | password: {password} | role: {role.value}")

    await Tortoise.close_connections()
    print("\nAll test users recreated successfully!")

asyncio.run(init())

