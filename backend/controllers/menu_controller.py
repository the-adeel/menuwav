from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pathlib import Path
import tempfile
import os

from models.menu import Menu, MenuIn_Pydantic, Menu_Pydantic
from models.menu_item import MenuItem, MenuItemIn_Pydantic, MenuItem_Pydantic
from models.menu_item_addon import MenuItemAddon, MenuItemAddonIn_Pydantic, MenuItemAddon_Pydantic
from models.restaurant import Restaurant
from models.user import User, Role
from services.auth import get_current_user
from services.menu_import import import_menu_from_excel

router = APIRouter()

@router.get("/{restaurant_id}/public")
async def get_public_menu(restaurant_id: int):
    """Public endpoint for customers to view menu (no auth required)"""
    restaurant = await Restaurant.get_or_none(id=restaurant_id)
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")
    
    if not restaurant.is_approved:
        raise HTTPException(403, "Restaurant is not approved")
    
    menus = await Menu.filter(restaurant=restaurant).prefetch_related("items")
    result = []
    for menu in menus:
        items = await menu.items.all().prefetch_related("addons")
        items_data = []
        for item in items:
            item_dict = await MenuItem_Pydantic.from_tortoise_orm(item)
            addons = await item.addons.filter(is_available=True).all()
            items_data.append({
                **item_dict.dict(),
                "addons": [await MenuItemAddon_Pydantic.from_tortoise_orm(addon) for addon in addons]
            })
        result.append({
            "menu": await Menu_Pydantic.from_tortoise_orm(menu),
            "items": items_data
        })
    return result

@router.get("/{restaurant_id}")
async def get_menu(restaurant_id: int):
    restaurant = await Restaurant.get_or_none(id=restaurant_id)
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")
    
    menus = await Menu.filter(restaurant=restaurant).prefetch_related("items")
    result = []
    for menu in menus:
        items = await menu.items.all().prefetch_related("addons")
        items_data = []
        for item in items:
            item_dict = await MenuItem_Pydantic.from_tortoise_orm(item)
            addons = await item.addons.all()
            items_data.append({
                **item_dict.dict(),
                "addons": [await MenuItemAddon_Pydantic.from_tortoise_orm(addon) for addon in addons]
            })
        result.append({
            "menu": await Menu_Pydantic.from_tortoise_orm(menu),
            "items": items_data
        })
    return result

@router.post("/{restaurant_id}/menus", response_model=Menu_Pydantic)
async def create_menu(restaurant_id: int, menu_in: MenuIn_Pydantic, user: User = Depends(get_current_user)):
    restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant or user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(403, "Not authorized")
    
    menu = await Menu.create(restaurant=restaurant, **menu_in.dict())
    return await Menu_Pydantic.from_tortoise_orm(menu)

@router.post("/{restaurant_id}/import")
async def import_menu_items(
    restaurant_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user)
):
    """
    Import menu items from Excel file
    
    Excel file format:
    - Column A: Menu Name
    - Column B: Item Name
    - Column C: Item Description
    - Column D: Item Price
    - Column E: Item Image (cell with embedded image)
    """
    # Verify authorization
    restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant or user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(403, "Not authorized")
    
    # Validate file type
    if not file.filename:
        raise HTTPException(400, "No file provided")
    
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ['.xlsx', '.xlsm']:
        raise HTTPException(400, "Invalid file type. Only .xlsx and .xlsm files are supported")
    
    # Save uploaded file to temporary location
    temp_file = None
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
            temp_file_path = temp_file.name
            # Write uploaded content to temp file
            content = await file.read()
            temp_file.write(content)
        
        # Import menu items
        result = await import_menu_from_excel(temp_file_path, restaurant)
        
        return result.to_dict()
    
    except Exception as e:
        raise HTTPException(500, f"Failed to import menu items: {str(e)}")
    
    finally:
        # Clean up temporary file
        if temp_file and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass

@router.post("/{restaurant_id}/menus/{menu_id}/items", response_model=MenuItem_Pydantic)
async def add_item(restaurant_id: int, menu_id: int, item_in: MenuItemIn_Pydantic, user: User = Depends(get_current_user)):
    restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant or user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(403, "Not authorized")
    
    menu = await Menu.get_or_none(id=menu_id, restaurant=restaurant)
    if not menu:
        raise HTTPException(404, "Menu not found")
    
    item = await MenuItem.create(menu=menu, **item_in.dict())
    return await MenuItem_Pydantic.from_tortoise_orm(item)

@router.put("/{restaurant_id}/menus/{menu_id}/items/{item_id}", response_model=MenuItem_Pydantic)
async def update_item(restaurant_id: int, menu_id: int, item_id: int, item_in: MenuItemIn_Pydantic, user: User = Depends(get_current_user)):
    restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant or user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(403, "Not authorized")
    
    menu = await Menu.get_or_none(id=menu_id, restaurant=restaurant)
    if not menu:
        raise HTTPException(404, "Menu not found")
    
    menu_item = await MenuItem.get_or_none(id=item_id, menu=menu)
    if not menu_item:
        raise HTTPException(404, "Menu item not found")
    
    item_data = item_in.dict()
    menu_item.name = item_data.get('name', menu_item.name)
    menu_item.description = item_data.get('description', menu_item.description)
    menu_item.price = item_data.get('price', menu_item.price)
    menu_item.image_url = item_data.get('image_url', menu_item.image_url)
    await menu_item.save()
    return await MenuItem_Pydantic.from_tortoise_orm(menu_item)

@router.post("/{restaurant_id}/menus/{menu_id}/items/{item_id}/addons", response_model=MenuItemAddon_Pydantic)
async def create_addon(restaurant_id: int, menu_id: int, item_id: int, addon_in: MenuItemAddonIn_Pydantic, user: User = Depends(get_current_user)):
    restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant or user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(403, "Not authorized")
    
    menu = await Menu.get_or_none(id=menu_id, restaurant=restaurant)
    if not menu:
        raise HTTPException(404, "Menu not found")
    
    menu_item = await MenuItem.get_or_none(id=item_id, menu=menu)
    if not menu_item:
        raise HTTPException(404, "Menu item not found")
    
    addon = await MenuItemAddon.create(menu_item=menu_item, **addon_in.dict())
    return await MenuItemAddon_Pydantic.from_tortoise_orm(addon)

@router.get("/{restaurant_id}/menus/{menu_id}/items/{item_id}/addons")
async def get_addons(restaurant_id: int, menu_id: int, item_id: int, user: User = Depends(get_current_user)):
    restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant or user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(403, "Not authorized")
    
    menu = await Menu.get_or_none(id=menu_id, restaurant=restaurant)
    if not menu:
        raise HTTPException(404, "Menu not found")
    
    menu_item = await MenuItem.get_or_none(id=item_id, menu=menu)
    if not menu_item:
        raise HTTPException(404, "Menu item not found")
    
    addons = await MenuItemAddon.filter(menu_item=menu_item).all()
    return [await MenuItemAddon_Pydantic.from_tortoise_orm(addon) for addon in addons]

@router.put("/{restaurant_id}/menus/{menu_id}/items/{item_id}/addons/{addon_id}", response_model=MenuItemAddon_Pydantic)
async def update_addon(restaurant_id: int, menu_id: int, item_id: int, addon_id: int, addon_in: MenuItemAddonIn_Pydantic, user: User = Depends(get_current_user)):
    restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant or user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(403, "Not authorized")
    
    menu = await Menu.get_or_none(id=menu_id, restaurant=restaurant)
    if not menu:
        raise HTTPException(404, "Menu not found")
    
    menu_item = await MenuItem.get_or_none(id=item_id, menu=menu)
    if not menu_item:
        raise HTTPException(404, "Menu item not found")
    
    addon = await MenuItemAddon.get_or_none(id=addon_id, menu_item=menu_item)
    if not addon:
        raise HTTPException(404, "Add-on not found")
    
    addon_data = addon_in.dict()
    addon.name = addon_data.get('name', addon.name)
    addon.description = addon_data.get('description', addon.description)
    addon.price_adjustment = addon_data.get('price_adjustment', addon.price_adjustment)
    addon.image_url = addon_data.get('image_url', addon.image_url)
    addon.is_available = addon_data.get('is_available', addon.is_available)
    await addon.save()
    return await MenuItemAddon_Pydantic.from_tortoise_orm(addon)

@router.delete("/{restaurant_id}/menus/{menu_id}/items/{item_id}/addons/{addon_id}")
async def delete_addon(restaurant_id: int, menu_id: int, item_id: int, addon_id: int, user: User = Depends(get_current_user)):
    restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant or user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(403, "Not authorized")
    
    menu = await Menu.get_or_none(id=menu_id, restaurant=restaurant)
    if not menu:
        raise HTTPException(404, "Menu not found")
    
    menu_item = await MenuItem.get_or_none(id=item_id, menu=menu)
    if not menu_item:
        raise HTTPException(404, "Menu item not found")
    
    addon = await MenuItemAddon.get_or_none(id=addon_id, menu_item=menu_item)
    if not addon:
        raise HTTPException(404, "Add-on not found")
    
    await addon.delete()
    return {"message": "Add-on deleted successfully"}