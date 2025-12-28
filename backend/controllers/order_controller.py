from fastapi import APIRouter, Depends, HTTPException, Query, Header
from typing import List, Optional
from pydantic import BaseModel
from decimal import Decimal
import jwt
import os
from dotenv import load_dotenv

from models.order import Order, Order_Pydantic, OrderStatus
from models.order_item import OrderItem, OrderItem_Pydantic
from models.order_item_addon import OrderItemAddon, OrderItemAddon_Pydantic
from models.restaurant import Restaurant
from models.menu_item import MenuItem
from models.menu_item_addon import MenuItemAddon
from models.user import User, Role
from services.auth import get_current_user

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

async def get_optional_user(authorization: Optional[str] = Header(default=None)) -> Optional[User]:
    """Optional authentication - returns user if token is valid, None otherwise"""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    token = authorization.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        user = await User.get_or_none(username=username)
        if user and user.role == Role.CUSTOMER:
            return user
    except:
        pass
    return None

router = APIRouter()

class OrderItemRequest(BaseModel):
    menu_item_id: int
    quantity: int
    selected_addon_ids: List[int] = []

class CreateOrderRequest(BaseModel):
    restaurant_id: int
    table_number: Optional[int] = None
    items: List[OrderItemRequest]

class UpdateOrderStatusRequest(BaseModel):
    status: str

@router.post("/orders/")
async def create_order(order_data: CreateOrderRequest, customer: Optional[User] = Depends(get_optional_user)):
    """Public endpoint - can be called with or without auth"""
    
    restaurant = await Restaurant.get_or_none(id=order_data.restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    if not restaurant.is_approved:
        raise HTTPException(status_code=403, detail="Restaurant is not approved")
    
    # Calculate total and validate items
    total = Decimal('0.00')
    order_items_data = []
    
    for item_req in order_data.items:
        menu_item = await MenuItem.get_or_none(id=item_req.menu_item_id)
        if not menu_item:
            raise HTTPException(status_code=404, detail=f"Menu item {item_req.menu_item_id} not found")
        
        # Verify menu item belongs to the restaurant
        menu = await menu_item.menu
        menu_restaurant = await menu.restaurant
        if menu_restaurant.id != restaurant.id:
            raise HTTPException(status_code=400, detail=f"Menu item {item_req.menu_item_id} does not belong to this restaurant")
        
        if item_req.quantity < 1:
            raise HTTPException(status_code=400, detail="Quantity must be at least 1")
        
        # Validate and get selected add-ons
        addon_total = Decimal('0.00')
        selected_addons = []
        if item_req.selected_addon_ids:
            addons = await MenuItemAddon.filter(
                id__in=item_req.selected_addon_ids,
                menu_item=menu_item,
                is_available=True
            ).all()
            
            if len(addons) != len(item_req.selected_addon_ids):
                raise HTTPException(status_code=400, detail="One or more selected add-ons are invalid or unavailable")
            
            for addon in addons:
                addon_total += Decimal(str(addon.price_adjustment))
                selected_addons.append({
                    'addon': addon,
                    'price_at_time': addon.price_adjustment
                })
        
        # Calculate item total: (item_price + addon_total) * quantity
        item_total = (Decimal(str(menu_item.price)) + addon_total) * item_req.quantity
        total += item_total
        
        order_items_data.append({
            'menu_item': menu_item,
            'quantity': item_req.quantity,
            'price_at_time': menu_item.price,
            'selected_addons': selected_addons
        })
    
    # Create order
    order = await Order.create(
        restaurant=restaurant,
        customer=customer,
        table_number=order_data.table_number,
        status=OrderStatus.PENDING,
        total=total
    )
    
    # Create order items and add-ons
    for item_data in order_items_data:
        order_item = await OrderItem.create(
            order=order,
            menu_item=item_data['menu_item'],
            quantity=item_data['quantity'],
            price_at_time=item_data['price_at_time']
        )
        
        # Create order item add-ons
        for addon_data in item_data['selected_addons']:
            await OrderItemAddon.create(
                order_item=order_item,
                addon=addon_data['addon'],
                price_at_time=addon_data['price_at_time']
            )
    
    # Fetch order with items for response
    order_items = await OrderItem.filter(order=order).prefetch_related("menu_item", "addons")
    order_dict = await Order_Pydantic.from_tortoise_orm(order)
    items_data = []
    for oi in order_items:
        item_dict = await OrderItem_Pydantic.from_tortoise_orm(oi)
        menu_item_dict = await oi.menu_item
        addons = await oi.addons.all().prefetch_related("addon")
        addons_data = []
        for oa in addons:
            addon = await oa.addon
            addons_data.append({
                "id": addon.id,
                "name": addon.name,
                "price_adjustment": str(oa.price_at_time)
            })
        items_data.append({
            **item_dict.dict(),
            "menu_item": {
                "id": menu_item_dict.id,
                "name": menu_item_dict.name,
                "description": menu_item_dict.description
            },
            "addons": addons_data
        })
    
    return {
        **order_dict.dict(),
        "items": items_data
    }

@router.get("/orders/my-orders")
async def get_my_orders(user: User = Depends(get_current_user)):
    if user.role != Role.CUSTOMER:
        raise HTTPException(status_code=403, detail="Only customers can view their orders")
    
    orders = await Order.filter(customer=user).prefetch_related("restaurant", "items").order_by("-created_at")
    result = []
    for order in orders:
        order_dict = await Order_Pydantic.from_tortoise_orm(order)
        restaurant = await order.restaurant
        items = await order.items.all().prefetch_related("menu_item", "addons")
        items_data = []
        for oi in items:
            item_dict = await OrderItem_Pydantic.from_tortoise_orm(oi)
            menu_item = await oi.menu_item
            addons = await oi.addons.all().prefetch_related("addon")
            addons_data = []
            for oa in addons:
                addon = await oa.addon
                addons_data.append({
                    "id": addon.id,
                    "name": addon.name,
                    "price_adjustment": str(oa.price_at_time)
                })
            items_data.append({
                **item_dict.dict(),
                "menu_item": {
                    "id": menu_item.id,
                    "name": menu_item.name,
                    "description": menu_item.description
                },
                "addons": addons_data
            })
        result.append({
            **order_dict.dict(),
            "restaurant_name": restaurant.name,
            "items": items_data
        })
    return result

@router.get("/restaurants/{restaurant_id}/orders")
async def get_restaurant_orders(
    restaurant_id: int,
    status: Optional[str] = Query(None),
    table_number: Optional[int] = Query(None),
    user: User = Depends(get_current_user)
):
    if user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(status_code=403, detail="Only restaurant admins can view restaurant orders")
    
    restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found or you don't have access")
    
    # Build filter
    filters = {"restaurant": restaurant}
    if status:
        try:
            filters["status"] = OrderStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    if table_number is not None:
        filters["table_number"] = table_number
    
    orders = await Order.filter(**filters).prefetch_related("customer", "items").order_by("-created_at")
    result = []
    for order in orders:
        order_dict = await Order_Pydantic.from_tortoise_orm(order)
        customer = await order.customer if order.customer_id else None
        items = await order.items.all().prefetch_related("menu_item", "addons")
        items_data = []
        for oi in items:
            item_dict = await OrderItem_Pydantic.from_tortoise_orm(oi)
            menu_item = await oi.menu_item
            addons = await oi.addons.all().prefetch_related("addon")
            addons_data = []
            for oa in addons:
                addon = await oa.addon
                addons_data.append({
                    "id": addon.id,
                    "name": addon.name,
                    "price_adjustment": str(oa.price_at_time)
                })
            items_data.append({
                **item_dict.dict(),
                "menu_item": {
                    "id": menu_item.id,
                    "name": menu_item.name,
                    "description": menu_item.description
                },
                "addons": addons_data
            })
        result.append({
            **order_dict.dict(),
            "customer_username": customer.username if customer else None,
            "items": items_data
        })
    return result

@router.patch("/orders/{order_id}/status")
async def update_order_status(order_id: int, status_data: UpdateOrderStatusRequest, user: User = Depends(get_current_user)):
    if user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(status_code=403, detail="Only restaurant admins can update order status")
    
    order = await Order.get_or_none(id=order_id).prefetch_related("restaurant")
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    restaurant = await order.restaurant
    if restaurant.owner_id != user.id:
        raise HTTPException(status_code=403, detail="You don't have access to this order")
    
    try:
        order.status = OrderStatus(status_data.status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    await order.save()
    return await Order_Pydantic.from_tortoise_orm(order)

