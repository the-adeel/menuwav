from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Body
from pathlib import Path
import tempfile
import os
from typing import List, Optional
from pydantic import BaseModel

from models.menu import Menu, MenuIn_Pydantic, Menu_Pydantic
from models.category import Category, CategoryIn_Pydantic, Category_Pydantic
from models.menu_item import MenuItem, MenuItemIn_Pydantic, MenuItem_Pydantic
from models.menu_item_addon import MenuItemAddon
from models.addon import Addon, Addon_Pydantic
from models.ingredient import Ingredient, Ingredient_Pydantic
from models.menu_item_ingredient import MenuItemIngredient
from models.meal_item import MealItem, MealItem_Pydantic
from models.menu_item_meal_item import MenuItemMealItem
from models.restaurant import Restaurant
from models.user import User, Role
from services.auth import get_current_user
from services.menu_import import import_menu_from_excel

class ItemCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    image_url: Optional[str] = None
    category_ids: List[int] = []  # List of category IDs
    menu_id: Optional[int] = None  # Menu ID for import/organization (keep for backward compatibility)
    ingredient_ids: Optional[List[int]] = []
    addon_ids: Optional[List[int]] = []
    external_id: Optional[str] = None
    meal_item_ids: Optional[List[int]] = []

class ItemUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    image_url: Optional[str] = None
    category_ids: Optional[List[int]] = None  # List of category IDs
    menu_id: Optional[int] = None  # Menu ID for import/organization
    ingredient_ids: Optional[List[int]] = None
    addon_ids: Optional[List[int]] = None
    meal_item_ids: Optional[List[int]] = None
    external_id: Optional[str] = None

router = APIRouter()

@router.get("/{restaurant_id}/public")
async def get_public_menu(restaurant_id: int):
    """Public endpoint for customers to view menu (no auth required)"""
    restaurant = await Restaurant.get_or_none(id=restaurant_id)
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")
    
    if not restaurant.is_approved:
        raise HTTPException(403, "Restaurant is not approved")
    
    # Get all categories for this restaurant
    categories = await Category.filter(restaurant=restaurant).all()
    
    # Get all items for this restaurant (through menu relationship)
    all_items = await MenuItem.filter(menu__restaurant=restaurant).prefetch_related("categories").distinct()
    
    result = []
    for category in categories:
        # Get items for this specific category
        items = await MenuItem.filter(categories__id=category.id, menu__restaurant=restaurant).prefetch_related("categories").distinct()
        items_data = []
        for item in items:
            item_dict = await MenuItem_Pydantic.from_tortoise_orm(item)
            # Get addons for this item via junction table
            menu_item_addons = await MenuItemAddon.filter(menu_item=item).prefetch_related("addon")
            addons = []
            for mia in menu_item_addons:
                addon = await mia.addon
                if addon.is_available:
                    addons.append(await Addon_Pydantic.from_tortoise_orm(addon))
            # Get ingredients for this item
            menu_item_ingredients = await MenuItemIngredient.filter(menu_item=item).prefetch_related("ingredient")
            ingredients = [await Ingredient_Pydantic.from_tortoise_orm(mi.ingredient) for mi in menu_item_ingredients]
            # Get meal items for this item
            menu_item_meal_items = await MenuItemMealItem.filter(menu_item=item).prefetch_related("meal_item")
            meal_items = []
            for mim in menu_item_meal_items:
                meal_item = await mim.meal_item
                if meal_item.is_available:
                    meal_items.append(await MealItem_Pydantic.from_tortoise_orm(meal_item))
            items_data.append({
                **item_dict.dict(),
                "addons": [addon.dict() for addon in addons],
                "ingredients": [ing.dict() for ing in ingredients],
                "meal_items": [meal.dict() for meal in meal_items]
            })
        result.append({
            "category": await Category_Pydantic.from_tortoise_orm(category),
            "items": items_data
        })
    
    # Add "all items" section for the "All" tab
    all_items_data = []
    for item in all_items:
        item_dict = await MenuItem_Pydantic.from_tortoise_orm(item)
        # Get addons for this item via junction table
        menu_item_addons = await MenuItemAddon.filter(menu_item=item).prefetch_related("addon")
        addons = []
        for mia in menu_item_addons:
            addon = await mia.addon
            if addon.is_available:
                addons.append(await Addon_Pydantic.from_tortoise_orm(addon))
        menu_item_ingredients = await MenuItemIngredient.filter(menu_item=item).prefetch_related("ingredient")
        ingredients = [await Ingredient_Pydantic.from_tortoise_orm(mi.ingredient) for mi in menu_item_ingredients]
        menu_item_meal_items = await MenuItemMealItem.filter(menu_item=item).prefetch_related("meal_item")
        meal_items = []
        for mim in menu_item_meal_items:
            meal_item = await mim.meal_item
            if meal_item.is_available:
                meal_items.append(await MealItem_Pydantic.from_tortoise_orm(meal_item))
        all_items_data.append({
            **item_dict.dict(),
            "addons": [addon.dict() for addon in addons],
            "ingredients": [ing.dict() for ing in ingredients],
            "meal_items": [meal.dict() for meal in meal_items]
        })
    
    # Return categories with their items, plus all_items list
    return {
        "categories": result,
        "all_items": all_items_data
    }

@router.get("/{restaurant_id}")
async def get_menu(restaurant_id: int):
    restaurant = await Restaurant.get_or_none(id=restaurant_id)
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")
    
    menus = await Menu.filter(restaurant=restaurant).all()
    result = []
    for menu in menus:
        items = await MenuItem.filter(menu_id=menu.id).prefetch_related("categories").distinct()
        items_data = []
        for item in items:
            item_dict = await MenuItem_Pydantic.from_tortoise_orm(item)
            # Get addons for this item via junction table
            menu_item_addons = await MenuItemAddon.filter(menu_item=item).prefetch_related("addon")
            addons = []
            for mia in menu_item_addons:
                addon = await mia.addon
                addons.append(await Addon_Pydantic.from_tortoise_orm(addon))
            # Get ingredients for this item
            menu_item_ingredients = await MenuItemIngredient.filter(menu_item=item).prefetch_related("ingredient")
            ingredients = [await Ingredient_Pydantic.from_tortoise_orm(mi.ingredient) for mi in menu_item_ingredients]
            # Get meal items for this item
            menu_item_meal_items = await MenuItemMealItem.filter(menu_item=item).prefetch_related("meal_item")
            meal_items = []
            for mim in menu_item_meal_items:
                meal_item = await mim.meal_item
                if meal_item.is_available:
                    meal_items.append(await MealItem_Pydantic.from_tortoise_orm(meal_item))
            items_data.append({
                **item_dict.dict(),
                "addons": [addon.dict() for addon in addons],
                "ingredients": [ing.dict() for ing in ingredients],
                "meal_items": [meal.dict() for meal in meal_items]
            })
        result.append({
            "menu": await Menu_Pydantic.from_tortoise_orm(menu),
            "items": items_data
        })
    return result

@router.post("/{restaurant_id}/menus", response_model=Menu_Pydantic)
async def create_menu(restaurant_id: int, menu_in: MenuIn_Pydantic, user: User = Depends(get_current_user)):
    if user.role == Role.SUPERADMIN:
        restaurant = await Restaurant.get_or_none(id=restaurant_id)
    else:
        restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")
    if user.role != Role.SUPERADMIN and user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(403, "Not authorized")
    
    menu = await Menu.create(restaurant=restaurant, **menu_in.dict())
    return await Menu_Pydantic.from_tortoise_orm(menu)

@router.put("/{restaurant_id}/menus/{menu_id}", response_model=Menu_Pydantic)
async def update_menu(restaurant_id: int, menu_id: int, menu_in: MenuIn_Pydantic, user: User = Depends(get_current_user)):
    if user.role == Role.SUPERADMIN:
        restaurant = await Restaurant.get_or_none(id=restaurant_id)
    else:
        restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")
    if user.role != Role.SUPERADMIN and user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(403, "Not authorized")
    
    menu = await Menu.get_or_none(id=menu_id, restaurant=restaurant)
    if not menu:
        raise HTTPException(404, "Category not found")
    
    menu.name = menu_in.name
    await menu.save()
    return await Menu_Pydantic.from_tortoise_orm(menu)

@router.get("/{restaurant_id}/menus")
async def list_menus(restaurant_id: int, user: User = Depends(get_current_user)):
    if user.role == Role.SUPERADMIN:
        restaurant = await Restaurant.get_or_none(id=restaurant_id)
    else:
        restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")
    if user.role != Role.SUPERADMIN and user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(403, "Not authorized")
    
    menus = await Menu.filter(restaurant=restaurant).all()
    result = []
    for menu in menus:
        item_count = await MenuItem.filter(menu_id=menu.id).count()
        menu_dict = await Menu_Pydantic.from_tortoise_orm(menu)
        result.append({
            **menu_dict.dict(),
            "item_count": item_count
        })
    return result

@router.delete("/{restaurant_id}/menus/{menu_id}")
async def delete_menu(restaurant_id: int, menu_id: int, user: User = Depends(get_current_user)):
    if user.role == Role.SUPERADMIN:
        restaurant = await Restaurant.get_or_none(id=restaurant_id)
    else:
        restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")
    if user.role != Role.SUPERADMIN and user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(403, "Not authorized")
    
    menu = await Menu.get_or_none(id=menu_id, restaurant=restaurant)
    if not menu:
        raise HTTPException(404, "Menu not found")
    
    # Delete all items in this menu (Menu is for import/organization)
    await MenuItem.filter(menu=menu).delete()
    
    # Delete the menu itself
    await menu.delete()
    return {"message": "Menu deleted successfully"}

# Category Management Endpoints
@router.post("/{restaurant_id}/categories", response_model=Category_Pydantic)
async def create_category(restaurant_id: int, category_in: CategoryIn_Pydantic, user: User = Depends(get_current_user)):
    if user.role == Role.SUPERADMIN:
        restaurant = await Restaurant.get_or_none(id=restaurant_id)
    else:
        restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")
    if user.role != Role.SUPERADMIN and user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(403, "Not authorized")
    
    category = await Category.create(restaurant=restaurant, **category_in.dict())
    return await Category_Pydantic.from_tortoise_orm(category)

@router.get("/{restaurant_id}/categories")
async def list_categories(restaurant_id: int, user: User = Depends(get_current_user)):
    if user.role == Role.SUPERADMIN:
        restaurant = await Restaurant.get_or_none(id=restaurant_id)
    else:
        restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")
    if user.role != Role.SUPERADMIN and user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(403, "Not authorized")
    
    categories = await Category.filter(restaurant=restaurant).all()
    result = []
    for category in categories:
        item_count = await MenuItem.filter(categories__id=category.id).count()
        category_dict = await Category_Pydantic.from_tortoise_orm(category)
        result.append({
            **category_dict.dict(),
            "item_count": item_count
        })
    return result

@router.put("/{restaurant_id}/categories/{category_id}", response_model=Category_Pydantic)
async def update_category(restaurant_id: int, category_id: int, category_in: CategoryIn_Pydantic, user: User = Depends(get_current_user)):
    if user.role == Role.SUPERADMIN:
        restaurant = await Restaurant.get_or_none(id=restaurant_id)
    else:
        restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")
    if user.role != Role.SUPERADMIN and user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(403, "Not authorized")
    
    category = await Category.get_or_none(id=category_id, restaurant=restaurant)
    if not category:
        raise HTTPException(404, "Category not found")
    
    category.name = category_in.name
    await category.save()
    return await Category_Pydantic.from_tortoise_orm(category)

@router.delete("/{restaurant_id}/categories/{category_id}")
async def delete_category(restaurant_id: int, category_id: int, user: User = Depends(get_current_user)):
    if user.role == Role.SUPERADMIN:
        restaurant = await Restaurant.get_or_none(id=restaurant_id)
    else:
        restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")
    if user.role != Role.SUPERADMIN and user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(403, "Not authorized")
    
    category = await Category.get_or_none(id=category_id, restaurant=restaurant)
    if not category:
        raise HTTPException(404, "Category not found")
    
    # Remove category association from all items (items may belong to other categories too)
    menu_items = await MenuItem.filter(categories__id=category_id).prefetch_related("categories").all()
    for item in menu_items:
        await item.categories.remove(category)
    
    # Delete the category itself
    await category.delete()
    return {"message": "Category deleted successfully"}

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
    if user.role == Role.SUPERADMIN:
        restaurant = await Restaurant.get_or_none(id=restaurant_id)
    else:
        restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")
    if user.role != Role.SUPERADMIN and user.role != Role.RESTAURANT_ADMIN:
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

@router.post("/{restaurant_id}/items", response_model=MenuItem_Pydantic)
async def add_item(restaurant_id: int, item_request: ItemCreateRequest, user: User = Depends(get_current_user)):
    if user.role == Role.SUPERADMIN:
        restaurant = await Restaurant.get_or_none(id=restaurant_id)
    else:
        restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")
    if user.role != Role.SUPERADMIN and user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(403, "Not authorized")
    
    # Validate menu_id if provided (required for organization/import)
    menu = None
    if item_request.menu_id:
        menu = await Menu.get_or_none(id=item_request.menu_id, restaurant=restaurant)
        if not menu:
            raise HTTPException(400, "Menu not found or not authorized")
    
    # Validate category_ids belong to this restaurant
    categories = []
    if item_request.category_ids:
        categories = await Category.filter(id__in=item_request.category_ids, restaurant=restaurant).all()
        if len(categories) != len(item_request.category_ids):
            raise HTTPException(400, "One or more categories not found or not authorized")
    
    # Check for duplicate external_id if provided
    if item_request.external_id:
        existing_item = await MenuItem.filter(
            menu__restaurant=restaurant,
            external_id=item_request.external_id
        ).first()
        if existing_item:
            raise HTTPException(400, f"Menu item with ID '{item_request.external_id}' already exists")
    
    # Create the menu item
    item = await MenuItem.create(
        name=item_request.name,
        description=item_request.description,
        price=item_request.price,
        image_url=item_request.image_url,
        external_id=item_request.external_id,
        menu=menu
    )
    
    # Associate item with categories
    if categories:
        await item.categories.add(*categories)
    
    # Add ingredients if provided
    if item_request.ingredient_ids:
        # Verify all ingredients belong to this restaurant
        ingredients = await Ingredient.filter(id__in=item_request.ingredient_ids, restaurant=restaurant).all()
        if len(ingredients) != len(item_request.ingredient_ids):
            raise HTTPException(400, "One or more ingredients not found or not authorized")
        
        # Create ingredient relationships
        for ingredient in ingredients:
            await MenuItemIngredient.create(menu_item=item, ingredient=ingredient)
    
    # Add add-ons if provided
    if item_request.addon_ids:
        # Verify all addons belong to this restaurant
        addons = await Addon.filter(id__in=item_request.addon_ids, restaurant=restaurant).all()
        if len(addons) != len(item_request.addon_ids):
            raise HTTPException(400, "One or more addons not found or not authorized")
        
        # Create addon relationships
        for addon in addons:
            await MenuItemAddon.create(menu_item=item, addon=addon)
    
    # Add meal items if provided
    if item_request.meal_item_ids:
        # Verify all meal items belong to this restaurant
        meal_items = await MealItem.filter(id__in=item_request.meal_item_ids, restaurant=restaurant).all()
        if len(meal_items) != len(item_request.meal_item_ids):
            raise HTTPException(400, "One or more meal items not found or not authorized")
        
        # Create meal item relationships
        for meal_item in meal_items:
            await MenuItemMealItem.create(menu_item=item, meal_item=meal_item)
    
    return await MenuItem_Pydantic.from_tortoise_orm(item)

@router.put("/{restaurant_id}/items/{item_id}", response_model=MenuItem_Pydantic)
async def update_item(restaurant_id: int, item_id: int, item_request: ItemUpdateRequest, user: User = Depends(get_current_user)):
    if user.role == Role.SUPERADMIN:
        restaurant = await Restaurant.get_or_none(id=restaurant_id)
    else:
        restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")
    if user.role != Role.SUPERADMIN and user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(403, "Not authorized")
    
    # Get item and verify it belongs to this restaurant (through menu relationship)
    menu_item = await MenuItem.filter(id=item_id, menu__restaurant=restaurant).prefetch_related("categories").first()
    if not menu_item:
        raise HTTPException(404, "Menu item not found")
    
    # Check for duplicate external_id if provided and different from current
    if item_request.external_id is not None and item_request.external_id != menu_item.external_id:
        existing_item = await MenuItem.filter(
            menu__restaurant=restaurant,
            external_id=item_request.external_id
        ).first()
        if existing_item and existing_item.id != menu_item.id:
            raise HTTPException(400, f"Menu item with ID '{item_request.external_id}' already exists")
    
    # Update basic fields
    if item_request.name is not None:
        menu_item.name = item_request.name
    if item_request.description is not None:
        menu_item.description = item_request.description
    if item_request.price is not None:
        menu_item.price = item_request.price
    if item_request.image_url is not None:
        menu_item.image_url = item_request.image_url
    if item_request.external_id is not None:
        menu_item.external_id = item_request.external_id
    if item_request.menu_id is not None:
        menu = await Menu.get_or_none(id=item_request.menu_id, restaurant=restaurant)
        if menu:
            menu_item.menu = menu
    await menu_item.save()
    
    # Update category associations if provided
    if item_request.category_ids is not None:
        # Validate category_ids belong to this restaurant
        if item_request.category_ids:
            categories = await Category.filter(id__in=item_request.category_ids, restaurant=restaurant).all()
            if len(categories) != len(item_request.category_ids):
                raise HTTPException(400, "One or more categories not found or not authorized")
        else:
            categories = []
        
        # Clear existing category associations and add new ones
        await menu_item.categories.clear()
        if categories:
            await menu_item.categories.add(*categories)
    
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
    
    # Update addons if provided
    if item_request.addon_ids is not None:
        # Delete existing addon relationships
        await MenuItemAddon.filter(menu_item=menu_item).delete()
        
        # Add new addon relationships
        if item_request.addon_ids:
            # Verify all addons belong to this restaurant
            addons = await Addon.filter(id__in=item_request.addon_ids, restaurant=restaurant).all()
            if len(addons) != len(item_request.addon_ids):
                raise HTTPException(400, "One or more addons not found or not authorized")
            
            # Create addon relationships
            for addon in addons:
                await MenuItemAddon.create(menu_item=menu_item, addon=addon)
    
    # Update meal items if provided
    if item_request.meal_item_ids is not None:
        # Delete existing meal item relationships
        await MenuItemMealItem.filter(menu_item=menu_item).delete()
        
        # Add new meal item relationships
        if item_request.meal_item_ids:
            # Verify all meal items belong to this restaurant
            meal_items = await MealItem.filter(id__in=item_request.meal_item_ids, restaurant=restaurant).all()
            if len(meal_items) != len(item_request.meal_item_ids):
                raise HTTPException(400, "One or more meal items not found or not authorized")
            
            # Create meal item relationships
            for meal_item in meal_items:
                await MenuItemMealItem.create(menu_item=menu_item, meal_item=meal_item)
    
    return await MenuItem_Pydantic.from_tortoise_orm(menu_item)

@router.delete("/{restaurant_id}/items/{item_id}")
async def delete_item(restaurant_id: int, item_id: int, user: User = Depends(get_current_user)):
    if user.role == Role.SUPERADMIN:
        restaurant = await Restaurant.get_or_none(id=restaurant_id)
    else:
        restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")
    if user.role != Role.SUPERADMIN and user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(403, "Not authorized")
    
    menu_item = await MenuItem.filter(id=item_id, menu__restaurant=restaurant).first()
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
    if user.role == Role.SUPERADMIN:
        restaurant = await Restaurant.get_or_none(id=restaurant_id)
    else:
        restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")
    if user.role != Role.SUPERADMIN and user.role != Role.RESTAURANT_ADMIN:
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