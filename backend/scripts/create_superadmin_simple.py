# create_superadmin_simple.py - Works with current DB schema (before migrations)
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

async def init():
    # Connect directly to database
    db_url = os.getenv("DB_URL")
    if not db_url:
        print("Error: DB_URL not found in .env file")
        return
    
    # Parse connection string
    # Format: postgresql://user:password@host:port/database
    conn = await asyncpg.connect(db_url)
    
    try:
        username = "superadmin"
        password = "super123"
        
        # Check if user exists
        existing = await conn.fetchrow(
            'SELECT id FROM "user" WHERE username = $1', username
        )
        
        if existing:
            print(f"Superadmin '{username}' already exists!")
            print(f"Credentials -> username: {username} | password: {password}")
        else:
            # Hash password
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Insert user (without email/phone since columns don't exist yet)
            await conn.execute(
                'INSERT INTO "user" (username, password, role) VALUES ($1, $2, $3)',
                username, hashed, 'superadmin'
            )
            print(f"Superadmin created successfully!")
            print(f"Credentials -> username: {username} | password: {password}")
    finally:
        await conn.close()

asyncio.run(init())

