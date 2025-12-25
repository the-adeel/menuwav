# test_login_direct.py - Test superadmin login with direct DB query
import asyncio
import sys
import os

script_dir = os.path.dirname(os.path.realpath(__file__))
backend_dir = os.path.dirname(script_dir)
sys.path.insert(0, backend_dir)

import bcrypt
from dotenv import load_dotenv
import asyncpg

load_dotenv()

async def test():
    db_url = os.getenv("DB_URL")
    if not db_url:
        print("Error: DB_URL not found in .env file")
        return
    
    conn = await asyncpg.connect(db_url)
    
    try:
        username = "superadmin"
        password = "super123"
        
        # Query user directly (only columns that exist)
        user_row = await conn.fetchrow(
            'SELECT id, username, password, role FROM "user" WHERE username = $1',
            username
        )
        
        if not user_row:
            print(f"ERROR: User '{username}' not found in database!")
            return
        
        print(f"User found: {user_row['username']}")
        print(f"User role: {user_row['role']}")
        print(f"Password hash: {user_row['password'][:30]}... (length: {len(user_row['password'])})")
        
        # Test password verification
        try:
            password_bytes = password.encode('utf-8')
            stored_hash_bytes = user_row['password'].encode('utf-8')
            password_valid = bcrypt.checkpw(password_bytes, stored_hash_bytes)
            print(f"Password verification: {password_valid}")
            
            if not password_valid:
                print("\nERROR: Password verification failed!")
                print("The stored hash doesn't match the password 'super123'")
            else:
                print("\nSUCCESS: Password verification passed!")
        except Exception as e:
            print(f"\nERROR during password verification: {e}")
            print(f"Error type: {type(e)}")
            import traceback
            traceback.print_exc()
            
    finally:
        await conn.close()

asyncio.run(test())

