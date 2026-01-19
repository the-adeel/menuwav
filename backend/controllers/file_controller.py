from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import FileResponse, Response
import os
import uuid
import shutil
import time
from pathlib import Path
from typing import Optional
import aiofiles

from models.restaurant import Restaurant
from models.user import User, Role
from services.auth import get_current_user

router = APIRouter()

# Allowed image extensions
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# Base upload directory
UPLOAD_BASE_DIR = Path("uploads/images")

def validate_image_file(file: UploadFile):
    """Validate image file type and size"""
    # Check file extension
    if not file.filename:
        return False, "No filename provided"
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return False, f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
    
    return True, None

async def save_uploaded_file(file: UploadFile, file_path: Path) -> None:
    """Save uploaded file asynchronously"""
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)

@router.post("/upload/menu-item-image")
async def upload_menu_item_image(
    file: UploadFile = File(...),
    restaurant_id: int = Form(...),
    user: User = Depends(get_current_user)
):
    """Upload image for menu item"""
    if user.role == Role.SUPERADMIN:
        restaurant = await Restaurant.get_or_none(id=restaurant_id)
    else:
        restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if user.role != Role.SUPERADMIN and user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(status_code=403, detail="Only restaurant admins can upload images")
    
    # Validate file
    is_valid, error_msg = validate_image_file(file)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Check file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File size exceeds {MAX_FILE_SIZE / 1024 / 1024}MB limit")
    
    # Create restaurant-specific directory
    restaurant_dir = UPLOAD_BASE_DIR / f"restaurant_{restaurant_id}"
    restaurant_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    file_ext = Path(file.filename).suffix.lower()
    timestamp = int(time.time())
    unique_id = str(uuid.uuid4())[:8]
    filename = f"menu_item_{timestamp}_{unique_id}{file_ext}"
    file_path = restaurant_dir / filename
    
    # Save file
    try:
        await save_uploaded_file(file, file_path)
        
        # Return relative path for URL
        relative_path = f"/uploads/images/restaurant_{restaurant_id}/{filename}"
        return {"image_url": relative_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

@router.post("/upload/addon-image")
async def upload_addon_image(
    file: UploadFile = File(...),
    restaurant_id: int = Form(...),
    addon_id: Optional[int] = Form(None),
    user: User = Depends(get_current_user)
):
    """Upload image for add-on"""
    if user.role == Role.SUPERADMIN:
        restaurant = await Restaurant.get_or_none(id=restaurant_id)
    else:
        restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if user.role != Role.SUPERADMIN and user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(status_code=403, detail="Only restaurant admins can upload images")
    
    # Validate file
    is_valid, error_msg = validate_image_file(file)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Check file size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File size exceeds {MAX_FILE_SIZE / 1024 / 1024}MB limit")
    
    # Create restaurant-specific addons directory
    restaurant_dir = UPLOAD_BASE_DIR / f"restaurant_{restaurant_id}" / "addons"
    restaurant_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    file_ext = Path(file.filename).suffix.lower()
    timestamp = int(time.time())
    unique_id = str(uuid.uuid4())[:8]
    addon_prefix = f"addon_{addon_id}_" if addon_id else "addon_"
    filename = f"{addon_prefix}{timestamp}_{unique_id}{file_ext}"
    file_path = restaurant_dir / filename
    
    # Save file
    try:
        await save_uploaded_file(file, file_path)
        
        # Return relative path for URL
        relative_path = f"/uploads/images/restaurant_{restaurant_id}/addons/{filename}"
        return {"image_url": relative_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

@router.post("/upload/restaurant-cover")
async def upload_restaurant_cover(
    file: UploadFile = File(...),
    restaurant_id: int = Form(...),
    user: User = Depends(get_current_user)
):
    """Upload cover photo for restaurant"""
    if user.role == Role.SUPERADMIN:
        restaurant = await Restaurant.get_or_none(id=restaurant_id)
    else:
        restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if user.role != Role.SUPERADMIN and user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(status_code=403, detail="Only restaurant admins can upload images")
    
    # Validate file
    is_valid, error_msg = validate_image_file(file)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Check file size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File size exceeds {MAX_FILE_SIZE / 1024 / 1024}MB limit")
    
    # Create restaurant-specific directory
    restaurant_dir = UPLOAD_BASE_DIR / f"restaurant_{restaurant_id}"
    restaurant_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    file_ext = Path(file.filename).suffix.lower()
    timestamp = int(time.time())
    unique_id = str(uuid.uuid4())[:8]
    filename = f"cover_{timestamp}_{unique_id}{file_ext}"
    file_path = restaurant_dir / filename
    
    # Save file
    try:
        await save_uploaded_file(file, file_path)
        
        # Update restaurant model with new cover photo URL
        relative_path = f"/uploads/images/restaurant_{restaurant_id}/{filename}"
        restaurant.cover_photo_url = relative_path
        await restaurant.save()
        
        return {"image_url": relative_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

@router.post("/upload/restaurant-logo")
async def upload_restaurant_logo(
    file: UploadFile = File(...),
    restaurant_id: int = Form(...),
    user: User = Depends(get_current_user)
):
    """Upload logo for restaurant"""
    if user.role == Role.SUPERADMIN:
        restaurant = await Restaurant.get_or_none(id=restaurant_id)
    else:
        restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if user.role != Role.SUPERADMIN and user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(status_code=403, detail="Only restaurant admins can upload images")
    
    # Validate file
    is_valid, error_msg = validate_image_file(file)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Check file size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File size exceeds {MAX_FILE_SIZE / 1024 / 1024}MB limit")
    
    # Create restaurant-specific directory
    restaurant_dir = UPLOAD_BASE_DIR / f"restaurant_{restaurant_id}"
    restaurant_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    file_ext = Path(file.filename).suffix.lower()
    timestamp = int(time.time())
    unique_id = str(uuid.uuid4())[:8]
    filename = f"logo_{timestamp}_{unique_id}{file_ext}"
    file_path = restaurant_dir / filename
    
    # Save file
    try:
        await save_uploaded_file(file, file_path)
        
        # Update restaurant model with new logo URL
        relative_path = f"/uploads/images/restaurant_{restaurant_id}/{filename}"
        restaurant.logo_url = relative_path
        await restaurant.save()
        
        return {"image_url": relative_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

@router.get("/proxy-image")
async def proxy_image(request: Request, image_path: str):
    """Proxy endpoint for images with CORS headers"""
    # Security: Only allow paths within uploads directory
    if not image_path.startswith("/uploads/"):
        raise HTTPException(status_code=400, detail="Invalid image path")
    
    # Remove leading slash and construct full path
    file_path = Path(image_path.lstrip("/"))
    
    # Ensure file exists
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Read file and return with CORS headers
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Determine content type
        content_type = "image/jpeg"
        if file_path.suffix.lower() == '.png':
            content_type = "image/png"
        elif file_path.suffix.lower() == '.webp':
            content_type = "image/webp"
        
        # Get origin from request
        origin = request.headers.get("origin", "*")
        
        # Return response with CORS headers
        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Credentials": "true",
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read image: {str(e)}")

