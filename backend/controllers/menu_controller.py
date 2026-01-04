from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Body
from pathlib import Path
import tempfile
import os
from typing import List, Optional
from pydantic import BaseModel

from models.menu import Menu, MenuIn_Pydantic, Menu_Pydantic
from models.menu_item import MenuItem, MenuItemIn_Pydantic, MenuItem_Pydantic
from models.menu_item_addon import MenuItemAddon, MenuItemAddonIn_Pydantic, MenuItemAddon_Pydantic
from models.ingredient import Ingredient, Ingredient_Pydantic
from models.menu_item_ingredient import MenuItemIngredient
from models.restaurant import Restaurant
from models.user import User, Role
from services.auth import get_current_user
from services.menu_import import import_menu_from_excel

class ItemCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    image_url: Optional[str] = None
    ingredient_ids: Optional[List[int]] = []
    addons: Optional[List[dict]] = []

class ItemUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    image_url: Optional[str] = None
    ingredient_ids: Optional[List[int]] = None

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
            # Get ingredients for this item
            menu_item_ingredients = await MenuItemIngredient.filter(menu_item=item).prefetch_related("ingredient")
            ingredients = [await Ingredient_Pydantic.from_tortoise_orm(mi.ingredient) for mi in menu_item_ingredients]
            items_data.append({
                **item_dict.dict(),
                "addons": [await MenuItemAddon_Pydantic.from_tortoise_orm(addon) for addon in addons],
                "ingredients": [ing.dict() for ing in ingredients]
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
            # Get ingredients for this item
            menu_item_ingredients = await MenuItemIngredient.filter(menu_item=item).prefetch_related("ingredient")
            ingredients = [await Ingredient_Pydantic.from_tortoise_orm(mi.ingredient) for mi in menu_item_ingredients]
            items_data.append({
                **item_dict.dict(),
                "addons": [await MenuItemAddon_Pydantic.from_tortoise_orm(addon) for addon in addons],
                "ingredients": [ing.dict() for ing in ingredients]
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

@router.delete("/{restaurant_id}/menus/{menu_id}")
async def delete_menu(restaurant_id: int, menu_id: int, user: User = Depends(get_current_user)):
    restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant or user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(403, "Not authorized")
    
    menu = await Menu.get_or_none(id=menu_id, restaurant=restaurant)
    if not menu:
        raise HTTPException(404, "Menu not found")
    
    # Delete all addons for all items in this menu
    menu_items = await MenuItem.filter(menu=menu).all()
    for item in menu_items:
        await MenuItemAddon.filter(menu_item=item).delete()
    
    # Delete all items in this menu
    await MenuItem.filter(menu=menu).delete()
    
    # Delete the menu itself
    await menu.delete()
    return {"message": "Menu deleted successfully"}

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
async def add_item(restaurant_id: int, menu_id: int, item_request: ItemCreateRequest, user: User = Depends(get_current_user)):
    restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant or user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(403, "Not authorized")
    
    menu = await Menu.get_or_none(id=menu_id, restaurant=restaurant)
    if not menu:
        raise HTTPException(404, "Menu not found")
    
    # Create the menu item
    item = await MenuItem.create(
        menu=menu,
        name=item_request.name,
        description=item_request.description,
        price=item_request.price,
        image_url=item_request.image_url
    )
    
    # Add ingredients if provided
    if item_request.ingredient_ids:
        # Verify all ingredients belong to this restaurant
        ingredients = await Ingredient.filter(id__in=item_request.ingredient_ids, restaurant=restaurant).all()
        if len(ingredients) != len(item_request.ingredient_ids):
            raise HTTPException(400, "One or more ingredients not found or not authorized")
        
        # Create ingredient relationships
        for ingredient in ingredients:
            await MenuItemIngredient.create(menu_item=item, ingredient=ingredient)
    
    # Create add-ons if provided
    if item_request.addons:
        for addon_data in item_request.addons:
            await MenuItemAddon.create(
                menu_item=item,
                name=addon_data.get('name'),
                description=addon_data.get('description'),
                price_adjustment=addon_data.get('price_adjustment', 0),
                image_url=addon_data.get('image_url'),
                is_available=addon_data.get('is_available', True)
            )
    
    return await MenuItem_Pydantic.from_tortoise_orm(item)

@router.put("/{restaurant_id}/menus/{menu_id}/items/{item_id}", response_model=MenuItem_Pydantic)
async def update_item(restaurant_id: int, menu_id: int, item_id: int, item_request: ItemUpdateRequest, user: User = Depends(get_current_user)):
    restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant or user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(403, "Not authorized")
    
    menu = await Menu.get_or_none(id=menu_id, restaurant=restaurant)
    if not menu:
        raise HTTPException(404, "Menu not found")
    
    menu_item = await MenuItem.get_or_none(id=item_id, menu=menu)
    if not menu_item:
        raise HTTPException(404, "Menu item not found")
    
    # Update basic fields
    if item_request.name is not None:
        menu_item.name = item_request.name
    if item_request.description is not None:
        menu_item.description = item_request.description
    if item_request.price is not None:
        menu_item.price = item_request.price
    if item_request.image_url is not None:
        menu_item.image_url = item_request.image_url
    await menu_item.save()
    
    # Update ingredients if provided
    if item_request.ingredient_ids is not None:
        # Delete existing ingredient relationships
        await MenuItemIngredient.filter(menu_item=menu_item).delete()
        
        # Add new ingredient relationships
        if item_request.ingredient_ids:
            # Verify all ingredients belong to this restaurant
            ingredients = await Ingredient.filter(id__in=item_request.ingredient_ids, restaurant=restaurant).all()
            if len(ingredients) != len(item_request.ingredient_ids):
                raise HTTPException(400, "One or more ingredients not found or not authorized")
            
            # Create ingredient relationships
            for ingredient in ingredients:
                await MenuItemIngredient.create(menu_item=menu_item, ingredient=ingredient)
    
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

@router.delete("/{restaurant_id}/menus/{menu_id}/items/{item_id}")
async def delete_item(restaurant_id: int, menu_id: int, item_id: int, user: User = Depends(get_current_user)):
    restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant or user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(403, "Not authorized")
    
    menu = await Menu.get_or_none(id=menu_id, restaurant=restaurant)
    if not menu:
        raise HTTPException(404, "Menu not found")
    
    menu_item = await MenuItem.get_or_none(id=item_id, menu=menu)
    if not menu_item:
        raise HTTPException(404, "Menu item not found")
    
    await menu_item.delete()
    return {"message": "Menu item deleted successfully"}

@router.post("/{restaurant_id}/menus/{menu_id}/items/delete")
async def delete_items_bulk(
    restaurant_id: int, 
    menu_id: int, 
    item_ids: list[int] = Body(...), 
    user: User = Depends(get_current_user)
):
    restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant or user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(403, "Not authorized")
    
    menu = await Menu.get_or_none(id=menu_id, restaurant=restaurant)
    if not menu:
        raise HTTPException(404, "Menu not found")
    
    # Delete all items if item_ids is empty or contains -1 (delete all)
    if not item_ids or -1 in item_ids:
        deleted_count = await MenuItem.filter(menu=menu).count()
        await MenuItem.filter(menu=menu).delete()
        return {"message": f"All {deleted_count} menu items deleted successfully", "deleted_count": deleted_count}
    
    # Delete specific items
    deleted_count = await MenuItem.filter(id__in=item_ids, menu=menu).count()
    await MenuItem.filter(id__in=item_ids, menu=menu).delete()
    return {"message": f"{deleted_count} menu item(s) deleted successfully", "deleted_count": deleted_count}