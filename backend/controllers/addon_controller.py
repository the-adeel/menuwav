from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Optional
from pydantic import BaseModel
from decimal import Decimal

from models.addon import Addon, Addon_Pydantic, AddonIn_Pydantic
from models.restaurant import Restaurant
from models.user import User, Role
from services.auth import get_current_user

router = APIRouter()

class AddonCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    price_adjustment: Decimal = Decimal('0.00')
    image_url: Optional[str] = None
    is_available: bool = True

class AddonCreateBulkRequest(BaseModel):
    names: str  # Comma-separated string of addon names (for simple creation like ingredients)

@router.get("/{restaurant_id}/addons", response_model=List[Addon_Pydantic])
async def list_addons(restaurant_id: int, user: User = Depends(get_current_user)):
    if user.role == Role.SUPERADMIN:
        restaurant = await Restaurant.get_or_none(id=restaurant_id)
    else:
        restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")
    if user.role != Role.SUPERADMIN and user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(403, "Not authorized")
    
    addons = await Addon.filter(restaurant=restaurant).order_by("name")
    return [await Addon_Pydantic.from_tortoise_orm(addon) for addon in addons]

@router.post("/{restaurant_id}/addons")
async def create_addon(
    restaurant_id: int, 
    request: AddonCreateRequest = Body(...),
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
    
    # Check if addon already exists for this restaurant
    existing = await Addon.get_or_none(name=request.name, restaurant=restaurant)
    if existing:
        raise HTTPException(400, f"Add-on '{request.name}' already exists")
    
    addon = await Addon.create(
        name=request.name,
        description=request.description,
        price_adjustment=request.price_adjustment,
        image_url=request.image_url,
        is_available=request.is_available,
        restaurant=restaurant
    )
    return await Addon_Pydantic.from_tortoise_orm(addon)

@router.post("/{restaurant_id}/addons/bulk")
async def create_addons_bulk(
    restaurant_id: int, 
    request: AddonCreateBulkRequest = Body(...),
    user: User = Depends(get_current_user)
):
    """Create multiple addons from comma-separated names (mimics ingredient creation)"""
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
        raise HTTPException(400, "No addon names provided")
    
    created_addons = []
    skipped_addons = []
    
    for name in names:
        # Check if addon already exists for this restaurant
        existing = await Addon.get_or_none(name=name, restaurant=restaurant)
        if existing:
            skipped_addons.append(name)
            continue
        
        addon = await Addon.create(
            name=name,
            description=None,
            price_adjustment=Decimal('0.00'),
            image_url=None,
            is_available=True,
            restaurant=restaurant
        )
        created_addons.append(await Addon_Pydantic.from_tortoise_orm(addon))
    
    return {
        "created": created_addons,
        "skipped": skipped_addons,
        "message": f"Created {len(created_addons)} addon(s), skipped {len(skipped_addons)} duplicate(s)"
    }

@router.put("/{restaurant_id}/addons/{addon_id}", response_model=Addon_Pydantic)
async def update_addon(
    restaurant_id: int,
    addon_id: int,
    addon_in: AddonIn_Pydantic,
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
    
    addon = await Addon.get_or_none(id=addon_id, restaurant=restaurant)
    if not addon:
        raise HTTPException(404, "Add-on not found")
    
    # Check if new name already exists (excluding current addon)
    if addon_in.name != addon.name:
        existing = await Addon.get_or_none(name=addon_in.name, restaurant=restaurant)
        if existing:
            raise HTTPException(400, f"Add-on '{addon_in.name}' already exists")
    
    # Update fields
    addon.name = addon_in.name
    addon.description = addon_in.description
    addon.price_adjustment = addon_in.price_adjustment
    addon.image_url = addon_in.image_url
    addon.is_available = addon_in.is_available
    await addon.save()
    return await Addon_Pydantic.from_tortoise_orm(addon)

@router.delete("/{restaurant_id}/addons/{addon_id}")
async def delete_addon(
    restaurant_id: int,
    addon_id: int,
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
    
    addon = await Addon.get_or_none(id=addon_id, restaurant=restaurant)
    if not addon:
        raise HTTPException(404, "Add-on not found")
    
    await addon.delete()
    return {"message": "Add-on deleted successfully"}

