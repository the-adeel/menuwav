from fastapi import APIRouter, Depends, HTTPException

from models.menu import Menu, MenuIn_Pydantic, Menu_Pydantic
from models.menu_item import MenuItem, MenuItemIn_Pydantic, MenuItem_Pydantic
from models.restaurant import Restaurant
from models.user import User, Role
from services.auth import get_current_user

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
        items = await menu.items.all()
        result.append({
            "menu": await Menu_Pydantic.from_tortoise_orm(menu),
            "items": [await MenuItem_Pydantic.from_tortoise_orm(i) for i in items]
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
        items = await menu.items.all()
        result.append({
            "menu": await Menu_Pydantic.from_tortoise_orm(menu),
            "items": [await MenuItem_Pydantic.from_tortoise_orm(i) for i in items]
        })
    return result

@router.post("/{restaurant_id}/menus", response_model=Menu_Pydantic)
async def create_menu(restaurant_id: int, menu_in: MenuIn_Pydantic, user: User = Depends(get_current_user)):
    restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant or user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(403, "Not authorized")
    
    menu = await Menu.create(restaurant=restaurant, **menu_in.dict())
    return await Menu_Pydantic.from_tortoise_orm(menu)

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