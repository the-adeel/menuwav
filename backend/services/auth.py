from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt  # This is from PyJWT
from jwt.exceptions import InvalidTokenError as JWTError  # Alias for compatibility
import os
from dotenv import load_dotenv

from models.user import User, Role

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        if not token:
            print("get_current_user: No token provided")
            raise credentials_exception
        if not SECRET_KEY:
            print("get_current_user: SECRET_KEY is not set")
            raise credentials_exception
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role_str: str = payload.get("role")
        if username is None:
            print(f"get_current_user: No username in token payload: {payload}")
            raise credentials_exception
        print(f"get_current_user: Successfully decoded token for user '{username}' with role '{role_str}'")
    except JWTError as e:
        print(f"get_current_user: JWT decode error: {e}, token length: {len(token) if token else 0}")
        raise credentials_exception

    # Try to get user - if email/phone columns don't exist, use raw query
    user = None
    try:
        user = await User.get_or_none(username=username)
    except Exception as e:
        # If query fails due to missing columns, use raw SQL
        try:
            import asyncpg
            db_url = os.getenv("DB_URL")
            if db_url:
                conn = await asyncpg.connect(db_url)
                try:
                    user_row = await conn.fetchrow(
                        'SELECT id, username, password, role FROM "user" WHERE username = $1',
                        username
                    )
                    if user_row:
                        # Create a minimal user object from raw query
                        class MinimalUser:
                            def __init__(self, row):
                                self.id = row['id']
                                self.username = row['username']
                                self.password = row['password']
                                role_str = row['role']
                                self.role = Role(role_str) if isinstance(role_str, str) else role_str
                                self.email = None
                                self.phone = None
                        
                        user = MinimalUser(user_row)
                finally:
                    await conn.close()
        except Exception as raw_err:
            print(f"Raw query also failed in get_current_user: {raw_err}")
            raise credentials_exception

    if user is None:
        raise credentials_exception

    # Ensure role is set correctly
    if not hasattr(user.role, 'value'):
        user.role = Role(role_str) if isinstance(role_str, str) else Role(user.role)
    
    return user