from fastapi import APIRouter, Depends, HTTPException
from typing import List

from models.restaurant import Restaurant, RestaurantIn_Pydantic, Restaurant_Pydantic
from models.menu import Menu, Menu_Pydantic
from models.menu_item import MenuItem, MenuItem_Pydantic
from models.user import User, Role
from services.auth import get_current_user

router = APIRouter()

@router.get("/")
async def list_restaurants():
    restaurants = await Restaurant.all().prefetch_related("owner")
    result = []
    for restaurant in restaurants:
        try:
            restaurant_data = await Restaurant_Pydantic.from_tortoise_orm(restaurant)
            result.append(restaurant_data.dict())
        except Exception:
            # If Pydantic fails due to missing columns, create minimal dict
            owner_data = await restaurant.owner
            result.append({
                "id": restaurant.id,
                "name": restaurant.name,
                "is_approved": getattr(restaurant, 'is_approved', False),
                "owner_id": restaurant.owner_id,
                "owner_username": owner_data.username
            })
    return result

@router.get("/pending")
async def get_pending_restaurants(user: User = Depends(get_current_user)):
    if user.role != Role.SUPERADMIN:
        raise HTTPException(status_code=403, detail="Only superadmin can view pending restaurants")
    
    try:
        # Try to filter by is_approved
        restaurants = await Restaurant.filter(is_approved=False).prefetch_related("owner")
    except Exception as e:
        # If is_approved column doesn't exist, get all restaurants (they're all pending)
        if "is_approved" in str(e):
            restaurants = await Restaurant.all().prefetch_related("owner")
        else:
            raise
    
    result = []
    for restaurant in restaurants:
        try:
            restaurant_data = await Restaurant_Pydantic.from_tortoise_orm(restaurant)
            restaurant_dict = restaurant_data.dict()
        except Exception:
            # If Pydantic fails due to missing columns, create minimal dict
            restaurant_dict = {
                "id": restaurant.id,
                "name": restaurant.name,
                "is_approved": getattr(restaurant, 'is_approved', False)
            }
        
        owner_data = await restaurant.owner
        result.append({
            **restaurant_dict,
            "owner_username": owner_data.username
        })
    return result

@router.post("/{restaurant_id}/approve")
async def approve_restaurant(restaurant_id: int, user: User = Depends(get_current_user)):
    if user.role != Role.SUPERADMIN:
        raise HTTPException(status_code=403, detail="Only superadmin can approve restaurants")
    
    restaurant = await Restaurant.get_or_none(id=restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    restaurant.is_approved = True
    await restaurant.save()
    return {"message": "Restaurant approved successfully"}

@router.post("/{restaurant_id}/disapprove")
async def disapprove_restaurant(restaurant_id: int, user: User = Depends(get_current_user)):
    if user.role != Role.SUPERADMIN:
        raise HTTPException(status_code=403, detail="Only superadmin can disapprove restaurants")
    
    restaurant = await Restaurant.get_or_none(id=restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    # Get owner before deleting restaurant
    owner = await restaurant.owner
    
    # Delete restaurant (this will cascade delete related data)
    await restaurant.delete()
    
    # Delete the restaurant owner user
    await owner.delete()
    
    return {"message": "Restaurant and owner deleted successfully"}

@router.get("/my-restaurant")
async def get_my_restaurant(user: User = Depends(get_current_user)):
    if user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(status_code=403, detail="Only restaurant admins can access this endpoint")
    
    restaurant = await Restaurant.get_or_none(owner=user)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    return await Restaurant_Pydantic.from_tortoise_orm(restaurant)

@router.get("/{restaurant_id}")
async def get_restaurant(restaurant_id: int):
    restaurant = await Restaurant.get_or_none(id=restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    # Get restaurant data
    try:
        restaurant_data = await Restaurant_Pydantic.from_tortoise_orm(restaurant)
        restaurant_dict = restaurant_data.dict()
    except Exception:
        # If Pydantic fails due to missing columns, create minimal dict
        restaurant_dict = {
            "id": restaurant.id,
            "name": restaurant.name,
            "is_approved": getattr(restaurant, 'is_approved', False)
        }
    
    # Get menus with items
    menus = await Menu.filter(restaurant=restaurant).prefetch_related("items")
    menus_data = []
    for menu in menus:
        items = await menu.items.all()
        menu_dict = await Menu_Pydantic.from_tortoise_orm(menu)
        menus_data.append({
            **menu_dict.dict(),
            "items": [await MenuItem_Pydantic.from_tortoise_orm(i) for i in items]
        })
    
    restaurant_dict["menus"] = menus_data
    return restaurant_dict

@router.post("/", response_model=Restaurant_Pydantic)
async def create_restaurant(restaurant_in: RestaurantIn_Pydantic, user: User = Depends(get_current_user)):
    if user.role != Role.SUPERADMIN:
        raise HTTPException(status_code=403, detail="Only superadmin can create restaurants")
    
    restaurant = await Restaurant.create(**restaurant_in.dict(), owner=user)
    return await Restaurant_Pydantic.from_tortoise_orm(restaurant)