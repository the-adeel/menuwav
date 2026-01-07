from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import uuid
import time
from pathlib import Path
import aiofiles
import base64

from models.generated_menu import GeneratedMenu, GeneratedMenu_Pydantic, GeneratedMenuIn_Pydantic
from models.restaurant import Restaurant
from models.user import User, Role
from services.auth import get_current_user

router = APIRouter()

# Base upload directory for generated menus
GENERATED_MENU_BASE_DIR = Path("uploads/generated_menus")

class GeneratedMenuCreateRequest(BaseModel):
    name: str
    orientation: str  # 'portrait' or 'wide'
    menu_item_ids: List[int]
    template_settings: dict

async def save_generated_menu_file(file_data: bytes, restaurant_id: int) -> str:
    """Save generated menu image file and return relative path"""
    # Create restaurant-specific directory
    restaurant_dir = GENERATED_MENU_BASE_DIR / f"restaurant_{restaurant_id}"
    restaurant_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    timestamp = int(time.time())
    unique_id = str(uuid.uuid4())[:8]
    filename = f"generated_menu_{timestamp}_{unique_id}.png"
    file_path = restaurant_dir / filename
    
    # Save file
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(file_data)
    
    # Return relative path for URL
    return f"/uploads/generated_menus/restaurant_{restaurant_id}/{filename}"

@router.post("/restaurants/{restaurant_id}/generated-menus")
async def create_generated_menu(
    restaurant_id: int,
    name: str = Form(...),
    orientation: str = Form(...),
    menu_item_ids: str = Form(...),  # JSON string
    template_settings: str = Form(...),  # JSON string
    image: UploadFile = File(...),
    user: User = Depends(get_current_user)
):
    """Save a generated menu image with metadata"""
    if user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(status_code=403, detail="Only restaurant admins can save generated menus")
    
    # Verify restaurant ownership
    restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found or you don't have access")
    
    # Validate orientation
    if orientation not in ['portrait', 'wide']:
        raise HTTPException(status_code=400, detail="Orientation must be 'portrait' or 'wide'")
    
    # Parse JSON fields
    import json
    try:
        menu_item_ids_list = json.loads(menu_item_ids)
        template_settings_dict = json.loads(template_settings)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON in request: {str(e)}")
    
    # Read image file
    image_data = await image.read()
    
    # Save file
    try:
        image_path = await save_generated_menu_file(image_data, restaurant_id)
        
        # Create database record
        generated_menu = await GeneratedMenu.create(
            restaurant=restaurant,
            name=name,
            orientation=orientation,
            image_path=image_path,
            menu_item_ids=menu_item_ids_list,
            template_settings=template_settings_dict
        )
        
        return await GeneratedMenu_Pydantic.from_tortoise_orm(generated_menu)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save generated menu: {str(e)}")

@router.get("/restaurants/{restaurant_id}/generated-menus")
async def list_generated_menus(
    restaurant_id: int,
    user: User = Depends(get_current_user)
):
    """List all generated menus for a restaurant"""
    if user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(status_code=403, detail="Only restaurant admins can view generated menus")
    
    # Verify restaurant ownership
    restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found or you don't have access")
    
    # Get all generated menus for this restaurant
    generated_menus = await GeneratedMenu.filter(restaurant=restaurant).order_by('-created_at')
    
    return [await GeneratedMenu_Pydantic.from_tortoise_orm(menu) for menu in generated_menus]

@router.get("/restaurants/{restaurant_id}/generated-menus/{menu_id}/download")
async def download_generated_menu(
    restaurant_id: int,
    menu_id: int,
    user: User = Depends(get_current_user)
):
    """Download a generated menu image"""
    if user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(status_code=403, detail="Only restaurant admins can download generated menus")
    
    # Verify restaurant ownership
    restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found or you don't have access")
    
    # Get the generated menu
    generated_menu = await GeneratedMenu.get_or_none(id=menu_id, restaurant=restaurant)
    if not generated_menu:
        raise HTTPException(status_code=404, detail="Generated menu not found")
    
    # Get file path (remove leading slash for Path)
    file_path = Path(generated_menu.image_path.lstrip('/'))
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Menu image file not found")
    
    return FileResponse(
        path=str(file_path),
        filename=f"{generated_menu.name}.png",
        media_type="image/png"
    )

@router.delete("/restaurants/{restaurant_id}/generated-menus/{menu_id}")
async def delete_generated_menu(
    restaurant_id: int,
    menu_id: int,
    user: User = Depends(get_current_user)
):
    """Delete a single generated menu"""
    if user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(status_code=403, detail="Only restaurant admins can delete generated menus")
    
    # Verify restaurant ownership
    restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found or you don't have access")
    
    # Get the generated menu
    generated_menu = await GeneratedMenu.get_or_none(id=menu_id, restaurant=restaurant)
    if not generated_menu:
        raise HTTPException(status_code=404, detail="Generated menu not found")
    
    # Delete file if it exists
    file_path = Path(generated_menu.image_path.lstrip('/'))
    if file_path.exists():
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Warning: Failed to delete file {file_path}: {e}")
    
    # Delete database record
    await generated_menu.delete()
    
    return {"message": "Generated menu deleted successfully"}

@router.delete("/restaurants/{restaurant_id}/generated-menus")
async def delete_generated_menus_bulk(
    restaurant_id: int,
    menu_ids: List[int] = Body(...),
    user: User = Depends(get_current_user)
):
    """Delete multiple generated menus"""
    if user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(status_code=403, detail="Only restaurant admins can delete generated menus")
    
    # Verify restaurant ownership
    restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found or you don't have access")
    
    # Get the generated menus
    generated_menus = await GeneratedMenu.filter(id__in=menu_ids, restaurant=restaurant).all()
    
    deleted_count = 0
    for menu in generated_menus:
        # Delete file if it exists
        file_path = Path(menu.image_path.lstrip('/'))
        if file_path.exists():
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Warning: Failed to delete file {file_path}: {e}")
        
        # Delete database record
        await menu.delete()
        deleted_count += 1
    
    return {"message": f"{deleted_count} generated menu(s) deleted successfully", "deleted_count": deleted_count}

