from fastapi import APIRouter, Depends, HTTPException, Body, Query
from typing import List, Optional
from pydantic import BaseModel
import re
import unicodedata

from models.restaurant import Restaurant, RestaurantIn_Pydantic, Restaurant_Pydantic
from models.menu import Menu, Menu_Pydantic
from models.menu_item import MenuItem, MenuItem_Pydantic
from models.menu_item_addon import MenuItemAddon
from models.addon import Addon, Addon_Pydantic
from models.user import User, Role
from services.auth import get_current_user

router = APIRouter()

class MealChargeUpdateRequest(BaseModel):
    meal_charge: float

class SubdomainUpdateRequest(BaseModel):
    subdomain: str

# Reserved subdomain names that cannot be used
RESERVED_SUBDOMAINS = {'www', 'api', 'admin', 'app', 'mail', 'ftp', 'localhost', '127', 'test', 'staging', 'dev'}

def slugify_subdomain(text: str) -> str:
    """Convert restaurant name to a valid subdomain slug."""
    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text)
    # Convert to lowercase
    text = text.lower()
    # Replace spaces and underscores with hyphens
    text = re.sub(r'[\s_]+', '-', text)
    # Remove all non-alphanumeric characters except hyphens
    text = re.sub(r'[^a-z0-9-]', '', text)
    # Remove multiple consecutive hyphens
    text = re.sub(r'-+', '-', text)
    # Remove leading and trailing hyphens
    text = text.strip('-')
    # Ensure minimum length of 3
    if len(text) < 3:
        text = text + '123'[:3-len(text)]
    # Truncate to 63 characters (max subdomain length)
    if len(text) > 63:
        text = text[:63].rstrip('-')
    return text

async def generate_unique_subdomain(base_name: str, exclude_restaurant_id: Optional[int] = None) -> str:
    """Generate a unique subdomain from restaurant name."""
    base_subdomain = slugify_subdomain(base_name)
    
    # Check if base subdomain is reserved
    if base_subdomain in RESERVED_SUBDOMAINS:
        base_subdomain = base_subdomain + '-restaurant'
    
    subdomain = base_subdomain
    counter = 1
    
    while True:
        # Check if subdomain exists
        existing = await Restaurant.get_or_none(subdomain=subdomain)
        if not existing or (exclude_restaurant_id and existing.id == exclude_restaurant_id):
            return subdomain
        
        # Append number if subdomain exists
        suffix = f'-{counter}'
        if len(base_subdomain) + len(suffix) > 63:
            # Truncate base if needed
            max_base_len = 63 - len(suffix)
            base_subdomain = base_subdomain[:max_base_len].rstrip('-')
        subdomain = base_subdomain + suffix
        counter += 1

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

@router.delete("/{restaurant_id}")
async def delete_restaurant(restaurant_id: int, user: User = Depends(get_current_user)):
    if user.role != Role.SUPERADMIN:
        raise HTTPException(status_code=403, detail="Only superadmin can delete restaurants")
    
    restaurant = await Restaurant.get_or_none(id=restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    # Get owner before deleting restaurant
    owner = await restaurant.owner
    
    # Delete restaurant (this will cascade delete related data like menus, items, orders, etc.)
    await restaurant.delete()
    
    # Delete the restaurant owner user
    await owner.delete()
    
    return {"message": "Restaurant and owner deleted successfully"}

@router.get("/my-restaurant")
async def get_my_restaurant(restaurant_id: Optional[int] = Query(None), user: User = Depends(get_current_user)):
    # If superadmin provides restaurant_id, allow access to that restaurant
    if user.role == Role.SUPERADMIN and restaurant_id is not None:
        restaurant = await Restaurant.get_or_none(id=restaurant_id)
        if not restaurant:
            raise HTTPException(status_code=404, detail="Restaurant not found")
        return await Restaurant_Pydantic.from_tortoise_orm(restaurant)
    
    # Otherwise, check if user is restaurant admin and get their restaurant
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
            "is_approved": getattr(restaurant, 'is_approved', False),
            "cover_photo_url": getattr(restaurant, 'cover_photo_url', None),
            "logo_url": getattr(restaurant, 'logo_url', None)
        }
    
    # Get menus with items and add-ons
    menus = await Menu.filter(restaurant=restaurant).prefetch_related("items")
    menus_data = []
    for menu in menus:
        items = await menu.items.all()
        items_data = []
        for item in items:
            item_dict = await MenuItem_Pydantic.from_tortoise_orm(item)
            # Get addons for this item via junction table
            menu_item_addons = await MenuItemAddon.filter(menu_item=item).prefetch_related("addon")
            addons = []
            for mia in menu_item_addons:
                addon = await mia.addon
                addons.append(await Addon_Pydantic.from_tortoise_orm(addon))
            items_data.append({
                **item_dict.dict(),
                "addons": [addon.dict() for addon in addons]
            })
        menu_dict = await Menu_Pydantic.from_tortoise_orm(menu)
        menus_data.append({
            **menu_dict.dict(),
            "items": items_data
        })
    
    restaurant_dict["menus"] = menus_data
    return restaurant_dict

@router.post("/", response_model=Restaurant_Pydantic)
async def create_restaurant(restaurant_in: RestaurantIn_Pydantic, user: User = Depends(get_current_user)):
    if user.role != Role.SUPERADMIN:
        raise HTTPException(status_code=403, detail="Only superadmin can create restaurants")
    
    restaurant = await Restaurant.create(**restaurant_in.dict(), owner=user)
    return await Restaurant_Pydantic.from_tortoise_orm(restaurant)

@router.patch("/{restaurant_id}/meal-charge", response_model=Restaurant_Pydantic)
async def update_meal_charge(
    restaurant_id: int,
    request: MealChargeUpdateRequest = Body(...),
    user: User = Depends(get_current_user)
):
    if user.role == Role.SUPERADMIN:
        restaurant = await Restaurant.get_or_none(id=restaurant_id)
    else:
        restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if user.role != Role.SUPERADMIN and user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(status_code=403, detail="Only restaurant admins can update meal charge")
    
    if request.meal_charge < 0:
        raise HTTPException(status_code=400, detail="Meal charge cannot be negative")
    
    restaurant.meal_charge = request.meal_charge
    await restaurant.save()
    return await Restaurant_Pydantic.from_tortoise_orm(restaurant)

@router.get("/by-subdomain/{subdomain}")
async def get_restaurant_by_subdomain(subdomain: str):
    """Get restaurant by subdomain (public endpoint)"""
    restaurant = await Restaurant.get_or_none(subdomain=subdomain)
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
            "subdomain": restaurant.subdomain,
            "is_approved": getattr(restaurant, 'is_approved', False),
            "cover_photo_url": getattr(restaurant, 'cover_photo_url', None),
            "logo_url": getattr(restaurant, 'logo_url', None)
        }
    
    return restaurant_dict

@router.patch("/{restaurant_id}/subdomain", response_model=Restaurant_Pydantic)
async def update_subdomain(
    restaurant_id: int,
    request: SubdomainUpdateRequest = Body(...),
    user: User = Depends(get_current_user)
):
    """Update restaurant subdomain"""
    if user.role == Role.SUPERADMIN:
        restaurant = await Restaurant.get_or_none(id=restaurant_id)
    else:
        restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if user.role != Role.SUPERADMIN and user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(status_code=403, detail="Only restaurant admins can update subdomain")
    
    # Validate and normalize subdomain
    subdomain = request.subdomain.lower().strip()
    
    # Validate subdomain format: 3-63 characters, lowercase alphanumeric with hyphens only
    if not re.match(r'^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$', subdomain):
        raise HTTPException(
            status_code=400,
            detail="Subdomain must be 3-63 characters, lowercase alphanumeric with hyphens only, and cannot start or end with a hyphen"
        )
    
    # Check if subdomain is reserved
    if subdomain in RESERVED_SUBDOMAINS:
        raise HTTPException(
            status_code=400,
            detail=f"Subdomain '{subdomain}' is reserved and cannot be used"
        )
    
    # Check if subdomain is already taken by another restaurant
    existing = await Restaurant.get_or_none(subdomain=subdomain)
    if existing and existing.id != restaurant_id:
        raise HTTPException(status_code=400, detail="Subdomain is already taken")
    
    restaurant.subdomain = subdomain
    await restaurant.save()
    return await Restaurant_Pydantic.from_tortoise_orm(restaurant)

@router.get("/{restaurant_id}/subdomain/suggest")
async def suggest_subdomain(
    restaurant_id: int,
    user: User = Depends(get_current_user)
):
    """Get suggested subdomain based on restaurant name"""
    if user.role == Role.SUPERADMIN:
        restaurant = await Restaurant.get_or_none(id=restaurant_id)
    else:
        restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if user.role != Role.SUPERADMIN and user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(status_code=403, detail="Only restaurant admins can access this endpoint")
    
    suggested = await generate_unique_subdomain(restaurant.name, exclude_restaurant_id=restaurant_id)
    return {"suggested_subdomain": suggested}