from fastapi import APIRouter, Depends, HTTPException, Body, UploadFile, File
from typing import List, Optional
from pydantic import BaseModel

from models.meal_item import MealItem, MealItem_Pydantic, MealItemIn_Pydantic
from models.restaurant import Restaurant
from models.user import User, Role
from services.auth import get_current_user

router = APIRouter()

class MealItemCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    image_url: Optional[str] = None
    is_available: bool = True

class MealItemUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    image_url: Optional[str] = None
    is_available: Optional[bool] = None

@router.get("/{restaurant_id}/meal-items", response_model=List[MealItem_Pydantic])
async def list_meal_items(restaurant_id: int, user: User = Depends(get_current_user)):
    if user.role == Role.SUPERADMIN:
        restaurant = await Restaurant.get_or_none(id=restaurant_id)
    else:
        restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")
    if user.role != Role.SUPERADMIN and user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(403, "Not authorized")
    
    meal_items = await MealItem.filter(restaurant=restaurant).order_by("name")
    return [await MealItem_Pydantic.from_tortoise_orm(item) for item in meal_items]

@router.post("/{restaurant_id}/meal-items", response_model=MealItem_Pydantic)
async def create_meal_item(
    restaurant_id: int, 
    request: MealItemCreateRequest = Body(...),
    user: User = Depends(get_current_user)
):
    if user.role == Role.SUPERADMIN:
        restaurant = await Restaurant.get_or_none(id=restaurant_id)
    else:
        restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")
    if user.role != Role.SUPERADMIN and user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(403, "Not authorized")
    
    # Check if meal item already exists for this restaurant
    existing = await MealItem.get_or_none(name=request.name, restaurant=restaurant)
    if existing:
        raise HTTPException(400, f"Meal item '{request.name}' already exists")
    
    meal_item = await MealItem.create(
        name=request.name,
        description=request.description,
        price=request.price,
        image_url=request.image_url,
        is_available=request.is_available,
        restaurant=restaurant
    )
    return await MealItem_Pydantic.from_tortoise_orm(meal_item)

@router.put("/{restaurant_id}/meal-items/{meal_item_id}", response_model=MealItem_Pydantic)
async def update_meal_item(
    restaurant_id: int,
    meal_item_id: int,
    request: MealItemUpdateRequest = Body(...),
    user: User = Depends(get_current_user)
):
    if user.role == Role.SUPERADMIN:
        restaurant = await Restaurant.get_or_none(id=restaurant_id)
    else:
        restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")
    if user.role != Role.SUPERADMIN and user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(403, "Not authorized")
    
    meal_item = await MealItem.get_or_none(id=meal_item_id, restaurant=restaurant)
    if not meal_item:
        raise HTTPException(404, "Meal item not found")
    
    # Check if new name already exists (excluding current meal item)
    if request.name and request.name != meal_item.name:
        existing = await MealItem.get_or_none(name=request.name, restaurant=restaurant)
        if existing:
            raise HTTPException(400, f"Meal item '{request.name}' already exists")
        meal_item.name = request.name
    
    if request.description is not None:
        meal_item.description = request.description
    if request.price is not None:
        meal_item.price = request.price
    if request.image_url is not None:
        meal_item.image_url = request.image_url
    if request.is_available is not None:
        meal_item.is_available = request.is_available
    
    await meal_item.save()
    return await MealItem_Pydantic.from_tortoise_orm(meal_item)

@router.delete("/{restaurant_id}/meal-items/{meal_item_id}")
async def delete_meal_item(
    restaurant_id: int,
    meal_item_id: int,
    user: User = Depends(get_current_user)
):
    if user.role == Role.SUPERADMIN:
        restaurant = await Restaurant.get_or_none(id=restaurant_id)
    else:
        restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")
    if user.role != Role.SUPERADMIN and user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(403, "Not authorized")
    
    meal_item = await MealItem.get_or_none(id=meal_item_id, restaurant=restaurant)
    if not meal_item:
        raise HTTPException(404, "Meal item not found")
    
    await meal_item.delete()
    return {"message": "Meal item deleted successfully"}

