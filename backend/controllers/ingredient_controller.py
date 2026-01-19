from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List
from pydantic import BaseModel

from models.ingredient import Ingredient, Ingredient_Pydantic, IngredientIn_Pydantic
from models.restaurant import Restaurant
from models.user import User, Role
from services.auth import get_current_user

router = APIRouter()

class IngredientCreateRequest(BaseModel):
    names: str  # Comma-separated string of ingredient names

@router.get("/{restaurant_id}/ingredients", response_model=List[Ingredient_Pydantic])
async def list_ingredients(restaurant_id: int, user: User = Depends(get_current_user)):
    if user.role == Role.SUPERADMIN:
        restaurant = await Restaurant.get_or_none(id=restaurant_id)
    else:
        restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")
    if user.role != Role.SUPERADMIN and user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(403, "Not authorized")
    
    ingredients = await Ingredient.filter(restaurant=restaurant).order_by("name")
    return [await Ingredient_Pydantic.from_tortoise_orm(ing) for ing in ingredients]

@router.post("/{restaurant_id}/ingredients")
async def create_ingredients(
    restaurant_id: int, 
    request: IngredientCreateRequest = Body(...),
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
    
    # Parse comma-separated names
    names = [name.strip() for name in request.names.split(",") if name.strip()]
    
    if not names:
        raise HTTPException(400, "No ingredient names provided")
    
    created_ingredients = []
    skipped_ingredients = []
    
    for name in names:
        # Check if ingredient already exists for this restaurant
        existing = await Ingredient.get_or_none(name=name, restaurant=restaurant)
        if existing:
            skipped_ingredients.append(name)
            continue
        
        ingredient = await Ingredient.create(name=name, restaurant=restaurant)
        created_ingredients.append(await Ingredient_Pydantic.from_tortoise_orm(ingredient))
    
    return {
        "created": created_ingredients,
        "skipped": skipped_ingredients,
        "message": f"Created {len(created_ingredients)} ingredient(s), skipped {len(skipped_ingredients)} duplicate(s)"
    }

@router.put("/{restaurant_id}/ingredients/{ingredient_id}", response_model=Ingredient_Pydantic)
async def update_ingredient(
    restaurant_id: int,
    ingredient_id: int,
    ingredient_in: IngredientIn_Pydantic,
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
    
    ingredient = await Ingredient.get_or_none(id=ingredient_id, restaurant=restaurant)
    if not ingredient:
        raise HTTPException(404, "Ingredient not found")
    
    # Check if new name already exists (excluding current ingredient)
    if ingredient_in.name != ingredient.name:
        existing = await Ingredient.get_or_none(name=ingredient_in.name, restaurant=restaurant)
        if existing:
            raise HTTPException(400, f"Ingredient '{ingredient_in.name}' already exists")
    
    ingredient.name = ingredient_in.name
    await ingredient.save()
    return await Ingredient_Pydantic.from_tortoise_orm(ingredient)

@router.delete("/{restaurant_id}/ingredients/{ingredient_id}")
async def delete_ingredient(
    restaurant_id: int,
    ingredient_id: int,
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
    
    ingredient = await Ingredient.get_or_none(id=ingredient_id, restaurant=restaurant)
    if not ingredient:
        raise HTTPException(404, "Ingredient not found")
    
    await ingredient.delete()
    return {"message": "Ingredient deleted successfully"}

