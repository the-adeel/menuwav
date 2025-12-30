from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
import bcrypt
import jwt  # PyJWT
from datetime import timedelta, datetime, timezone
import os
from dotenv import load_dotenv

from models.user import User, UserIn_Pydantic, User_Pydantic, Role
from models.restaurant import Restaurant
from services.auth import get_current_user
import asyncpg

load_dotenv()

router = APIRouter()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

class Token(BaseModel):
    access_token: str
    token_type: str

class SignUpRequest(BaseModel):
    username: str
    password: str
    role: str  # "customer" or "restaurant_admin"
    email: Optional[str] = None
    phone: Optional[str] = None
    # Restaurant-specific fields
    restaurant_name: Optional[str] = None
    address: Optional[str] = None

def create_access_token(data: dict):
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY is not set in environment variables")
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": int(expire.timestamp())})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    print(f"JWT token created successfully (length: {len(encoded_jwt)})")
    return encoded_jwt

@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # Try to get user - if email/phone columns don't exist, use raw query
    user = None
    user_data = None
    
    try:
        user = await User.get_or_none(username=form_data.username)
    except Exception as e:
        # If query fails due to missing columns, use raw SQL
        print(f"Tortoise query failed (likely missing columns), using raw query: {e}")
        try:
            db_url = os.getenv("DB_URL")
            if db_url:
                conn = await asyncpg.connect(db_url)
                try:
                    user_row = await conn.fetchrow(
                        'SELECT id, username, password, role FROM "user" WHERE username = $1',
                        form_data.username
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
                        
                        user = MinimalUser(user_row)
                finally:
                    await conn.close()
        except Exception as raw_err:
            print(f"Raw query also failed: {raw_err}")
    
    if not user:
        print(f"Login attempt: User '{form_data.username}' not found")
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    # Verify password using bcrypt
    try:
        # Ensure both are bytes for bcrypt.checkpw
        password_bytes = form_data.password.encode('utf-8')
        stored_hash_bytes = user.password.encode('utf-8')
        password_valid = bcrypt.checkpw(password_bytes, stored_hash_bytes)
        print(f"Password verification for '{form_data.username}': {password_valid}")
    except Exception as e:
        # Log the error for debugging (in production, don't expose this)
        print(f"Password verification error: {e}")
        print(f"Stored hash type: {type(user.password)}, length: {len(user.password) if user.password else 0}")
        password_valid = False
    
    if not password_valid:
        print(f"Login failed for '{form_data.username}': Invalid password")
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    # Get role value - handle both enum and string
    role_value = user.role.value if hasattr(user.role, 'value') else str(user.role)
    print(f"Login successful for '{form_data.username}' with role '{role_value}'")
    
    try:
        access_token = create_access_token({"sub": user.username, "role": role_value})
        response_data = {"access_token": access_token, "token_type": "bearer"}
        print(f"Returning login response with token")
        return response_data
    except Exception as token_err:
        print(f"Error creating access token: {token_err}")
        raise HTTPException(status_code=500, detail="Error creating access token")

@router.post("/signup")
async def signup(signup_data: SignUpRequest):
    try:
        if await User.exists(username=signup_data.username):
            raise HTTPException(status_code=400, detail="Username already taken")
        
        # Validate role
        if signup_data.role not in [Role.CUSTOMER.value, Role.RESTAURANT_ADMIN.value]:
            raise HTTPException(status_code=400, detail="Invalid role. Must be 'customer' or 'restaurant_admin'")
        
        # Validate restaurant fields if signing up as restaurant
        if signup_data.role == Role.RESTAURANT_ADMIN.value:
            if not signup_data.restaurant_name:
                raise HTTPException(status_code=400, detail="restaurant_name is required for restaurant signup")
        
        # Hash password
        hashed = bcrypt.hashpw(signup_data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Create user - handle missing email/phone columns
        try:
            user = await User.create(
                username=signup_data.username,
                password=hashed,
                role=Role(signup_data.role),
                email=signup_data.email,
                phone=signup_data.phone
            )
        except Exception as user_err:
            # If email/phone columns don't exist, create without them
            if "email" in str(user_err) or "phone" in str(user_err):
                user = await User.create(
                    username=signup_data.username,
                    password=hashed,
                    role=Role(signup_data.role)
                )
            else:
                raise
        
        # If restaurant admin, create restaurant
        if signup_data.role == Role.RESTAURANT_ADMIN.value:
            try:
                await Restaurant.create(
                    name=signup_data.restaurant_name,
                    owner=user,
                    is_approved=False,
                    address=signup_data.address,
                    phone=signup_data.phone,
                    email=signup_data.email
                )
            except Exception as rest_err:
                # If restaurant columns don't exist, create without them
                if "address" in str(rest_err) or "phone" in str(rest_err) or "email" in str(rest_err) or "is_approved" in str(rest_err):
                    await Restaurant.create(
                        name=signup_data.restaurant_name,
                        owner=user
                    )
                else:
                    raise
        
        # Return user data (without password)
        user_dict = {
            "id": user.id,
            "username": user.username,
            "role": user.role.value if hasattr(user.role, 'value') else str(user.role)
        }
        return user_dict
    except HTTPException:
        raise
    except Exception as e:
        print(f"Signup error: {e}")
        raise HTTPException(status_code=500, detail=f"Signup failed: {str(e)}")

@router.post("/register", response_model=User_Pydantic)
async def register(user_in: UserIn_Pydantic, current_user: User = Depends(get_current_user)):
    if current_user.role != Role.SUPERADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if await User.exists(username=user_in.username):
        raise HTTPException(status_code=400, detail="Username already taken")
    
    hashed = bcrypt.hashpw(user_in.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user = await User.create(username=user_in.username, password=hashed, role=user_in.role)
    return await User_Pydantic.from_tortoise_orm(user)

class CreateSuperadminRequest(BaseModel):
    username: str
    password: str
    admin_key: str

@router.post("/create-superadmin")
async def create_superadmin(request: CreateSuperadminRequest):
    """
    Create a superadmin user. Protected by ADMIN_CREATION_KEY from environment.
    This endpoint should be removed or disabled after initial setup.
    """
    # Check the admin key from environment
    ADMIN_CREATION_KEY = os.getenv("ADMIN_CREATION_KEY")
    if not ADMIN_CREATION_KEY:
        raise HTTPException(status_code=500, detail="Admin creation key not configured")
    
    if request.admin_key != ADMIN_CREATION_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    
    # Check if username already exists
    if await User.exists(username=request.username):
        raise HTTPException(status_code=400, detail="Username already taken")
    
    try:
        # Hash password
        hashed = bcrypt.hashpw(request.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Create superadmin user directly
        # Handle cases where email/phone columns might not exist
        try:
            user = await User.create(
                username=request.username,
                password=hashed,
                role=Role.SUPERADMIN,
                email=None,
                phone=None
            )
        except Exception as user_err:
            # If email/phone columns don't exist, create without them
            if "email" in str(user_err) or "phone" in str(user_err):
                user = await User.create(
                    username=request.username,
                    password=hashed,
                    role=Role.SUPERADMIN
                )
            else:
                raise
        
        return {
            "message": "Superadmin created successfully",
            "username": user.username,
            "id": user.id,
            "role": user.role.value if hasattr(user.role, 'value') else str(user.role)
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Create superadmin error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create superadmin: {str(e)}")