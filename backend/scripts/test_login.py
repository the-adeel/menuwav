# test_login.py - Test superadmin login
import asyncio
import sys
import os

script_dir = os.path.dirname(os.path.realpath(__file__))
backend_dir = os.path.dirname(script_dir)
sys.path.insert(0, backend_dir)

import bcrypt
from dotenv import load_dotenv
from tortoise import Tortoise
from helpers.tortoise_config import TORTOISE_ORM
from models.user import User, Role

load_dotenv()

async def test():
    await Tortoise.init(config=TORTOISE_ORM)
    
    username = "superadmin"
    password = "super123"
    
    # Get user
    user = await User.get_or_none(username=username)
    if not user:
        print(f"ERROR: User '{username}' not found in database!")
        await Tortoise.close_connections()
        return
    
    print(f"User found: {user.username}")
    print(f"User role: {user.role} (type: {type(user.role)})")
    print(f"Password hash: {user.password[:20]}... (length: {len(user.password)})")
    
    # Test password verification
    try:
        password_bytes = password.encode('utf-8')
        stored_hash_bytes = user.password.encode('utf-8')
        password_valid = bcrypt.checkpw(password_bytes, stored_hash_bytes)
        print(f"Password verification: {password_valid}")
        
        if not password_valid:
            print("\nERROR: Password verification failed!")
            print("This means the stored hash doesn't match the password.")
            print("You may need to recreate the superadmin with the correct password.")
    except Exception as e:
        print(f"\nERROR during password verification: {e}")
        print(f"Error type: {type(e)}")
    
    # Test role enum
    try:
        role_value = user.role.value if hasattr(user.role, 'value') else str(user.role)
        print(f"Role value for JWT: {role_value}")
    except Exception as e:
        print(f"ERROR getting role value: {e}")
    
    await Tortoise.close_connections()

asyncio.run(test())

