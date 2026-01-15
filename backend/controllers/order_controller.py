from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from decimal import Decimal

from models.order import Order, Order_Pydantic, OrderStatus, OrderType, PaymentStatus, PaymentMethod
from models.order_item import OrderItem, OrderItem_Pydantic
from models.order_item_addon import OrderItemAddon, OrderItemAddon_Pydantic
from models.order_meal_item import OrderMealItem, OrderMealItem_Pydantic
from models.restaurant import Restaurant
from models.menu_item import MenuItem
from models.menu_item_addon import MenuItemAddon
from models.meal_item import MealItem
from models.user import User, Role
from services.auth import get_current_user, get_optional_user

router = APIRouter()

def generate_order_number(restaurant_id: int, last_order_number: Optional[str] = None) -> str:
    """
    Generate next order number following pattern:
    A1-A9, B1-B9, ..., Z1-Z9, then A11-A19, B11-B19, ..., Z11-Z19, etc.
    (skipping numbers ending in 0)
    """
    import string
    
    if not last_order_number:
        # First order for this restaurant
        return "A1"
    
    # Extract letter and number from last order number
    letter = last_order_number[0]
    number_str = last_order_number[1:]
    
    try:
        number = int(number_str)
    except ValueError:
        # If parsing fails, start from A1
        return "A1"
    
    # Get letter index (A=0, B=1, ..., Z=25)
    letter_index = ord(letter.upper()) - ord('A')
    
    # Determine next number
    # Pattern: 1-9, then 11-19, 21-29, 31-39, etc. (skip numbers ending in 0)
    if number < 9:
        # Within 1-9 range, just increment
        next_number = number + 1
        return f"{letter}{next_number}"
    elif number == 9:
        # Move to next letter, start at 11 (skip 10)
        next_letter_index = (letter_index + 1) % 26
        next_letter = chr(ord('A') + next_letter_index)
        return f"{next_letter}11"
    else:
        # In 11-19, 21-29, etc. range
        # Check if we're at the end of a decade (19, 29, 39, etc.)
        if number % 10 == 9:
            # Move to next letter, start next decade
            next_letter_index = (letter_index + 1) % 26
            next_letter = chr(ord('A') + next_letter_index)
            # Start at next decade + 1 (e.g., after 19 comes 21, after 29 comes 31)
            next_decade = ((number // 10) + 1) * 10
            return f"{next_letter}{next_decade + 1}"
        else:
            # Just increment within current decade
            next_number = number + 1
            return f"{letter}{next_number}"

async def get_next_order_number(restaurant_id: int) -> str:
    """Get the next order number for a restaurant"""
    # Get the last order for this restaurant
    last_order = await Order.filter(restaurant_id=restaurant_id).order_by("-id").first()
    
    if not last_order or not last_order.order_number:
        # No previous orders or no order number set, start from A1
        return "A1"
    
    # Generate next number based on last order number
    return generate_order_number(restaurant_id, last_order.order_number)

class AddonRequest(BaseModel):
    id: int
    quantity: int = 1

class MealItemRequest(BaseModel):
    id: int
    quantity: int = 1

class OrderItemRequest(BaseModel):
    menu_item_id: int
    quantity: int
    selected_addon_ids: List[int] = []  # Legacy support - will be converted to selected_addons
    selected_addons: List[AddonRequest] = []  # New format with quantities
    selected_meal_items: List[MealItemRequest] = []  # Meal items for make a meal

class CreateOrderRequest(BaseModel):
    restaurant_id: int
    table_number: Optional[int] = None
    order_type: Optional[str] = "pickup"  # "pickup", "delivery", or "collection"
    items: List[OrderItemRequest]
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None

class UpdateOrderStatusRequest(BaseModel):
    status: str

class UpdatePaymentMethodRequest(BaseModel):
    payment_method: str  # "online" or "cash"

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
        
        # Support both old format (selected_addon_ids) and new format (selected_addons with quantities)
        addon_map = {}
        if item_req.selected_addons:
            # New format with quantities
            for addon_req in item_req.selected_addons:
                if addon_req.quantity < 1:
                    raise HTTPException(status_code=400, detail="Add-on quantity must be at least 1")
                if addon_req.quantity > 10:
                    raise HTTPException(status_code=400, detail="Add-on quantity cannot exceed 10")
                addon_map[addon_req.id] = addon_req.quantity
        elif item_req.selected_addon_ids:
            # Legacy format - default quantity 1 for each
            for addon_id in item_req.selected_addon_ids:
                addon_map[addon_id] = 1
        
        if addon_map:
            addon_ids = list(addon_map.keys())
            addons = await MenuItemAddon.filter(
                id__in=addon_ids,
                menu_item=menu_item,
                is_available=True
            ).all()
            
            if len(addons) != len(addon_ids):
                raise HTTPException(status_code=400, detail="One or more selected add-ons are invalid or unavailable")
            
            for addon in addons:
                quantity = addon_map[addon.id]
                addon_total += Decimal(str(addon.price_adjustment)) * quantity
                selected_addons.append({
                    'addon': addon,
                    'price_at_time': addon.price_adjustment,
                    'quantity': quantity
                })
        
        # Validate and get selected meal items
        meal_total = Decimal('0.00')
        selected_meal_items = []
        meal_charge = Decimal('0.00')
        
        if item_req.selected_meal_items:
            meal_item_ids = [mi.id for mi in item_req.selected_meal_items]
            meal_items = await MealItem.filter(
                id__in=meal_item_ids,
                restaurant=restaurant,
                is_available=True
            ).all()
            
            if len(meal_items) != len(meal_item_ids):
                raise HTTPException(status_code=400, detail="One or more selected meal items are invalid or unavailable")
            
            # Calculate meal items total
            meal_item_map = {mi.id: mi for mi in meal_items}
            for meal_item_req in item_req.selected_meal_items:
                if meal_item_req.quantity < 1:
                    raise HTTPException(status_code=400, detail="Meal item quantity must be at least 1")
                if meal_item_req.quantity > 10:
                    raise HTTPException(status_code=400, detail="Meal item quantity cannot exceed 10")
                
                meal_item = meal_item_map[meal_item_req.id]
                meal_total += Decimal(str(meal_item.price)) * meal_item_req.quantity
                selected_meal_items.append({
                    'meal_item': meal_item,
                    'price_at_time': meal_item.price,
                    'quantity': meal_item_req.quantity
                })
            
            # Add meal charge if meal items are selected
            if selected_meal_items and restaurant.meal_charge:
                meal_charge = Decimal(str(restaurant.meal_charge))
        
        # Calculate item total: (item_price + addon_total) * quantity + (meal_total + meal_charge) * quantity
        item_total = (Decimal(str(menu_item.price)) + addon_total) * item_req.quantity
        if selected_meal_items:
            item_total += (meal_total + meal_charge) * item_req.quantity
        total += item_total
        
        order_items_data.append({
            'menu_item': menu_item,
            'quantity': item_req.quantity,
            'price_at_time': menu_item.price,
            'selected_addons': selected_addons,
            'selected_meal_items': selected_meal_items,
            'meal_charge': meal_charge
        })
    
    # Validate order_type
    try:
        order_type = OrderType(order_data.order_type) if order_data.order_type else OrderType.PICKUP
    except ValueError:
        order_type = OrderType.PICKUP
    
    # Validate customer info for pickup and collection orders
    if order_type in [OrderType.PICKUP, OrderType.COLLECTION]:
        if not order_data.customer_name or not order_data.customer_name.strip():
            raise HTTPException(status_code=400, detail="Customer name is required for pickup and collection orders")
        if not order_data.customer_phone or not order_data.customer_phone.strip():
            raise HTTPException(status_code=400, detail="Customer phone is required for pickup and collection orders")
    
    # Generate order number
    order_number = await get_next_order_number(restaurant.id)
    
    # Create order
    order = await Order.create(
        restaurant=restaurant,
        customer=customer,
        table_number=order_data.table_number,
        status=OrderStatus.PENDING,
        total=total,
        order_type=order_type,
        payment_status=PaymentStatus.PENDING,
        order_number=order_number,
        customer_name=order_data.customer_name,
        customer_phone=order_data.customer_phone
    )
    
    # Create order items, add-ons, and meal items
    for item_data in order_items_data:
        order_item = await OrderItem.create(
            order=order,
            menu_item=item_data['menu_item'],
            quantity=item_data['quantity'],
            price_at_time=item_data['price_at_time'],
            meal_charge=item_data.get('meal_charge', Decimal('0.00'))
        )
        
        # Create order item add-ons
        for addon_data in item_data['selected_addons']:
            quantity = addon_data.get('quantity', 1)
            await OrderItemAddon.create(
                order_item=order_item,
                addon=addon_data['addon'],
                price_at_time=addon_data['price_at_time'],
                quantity=quantity
            )
        
        # Create order meal items
        for meal_item_data in item_data.get('selected_meal_items', []):
            quantity = meal_item_data.get('quantity', 1)
            await OrderMealItem.create(
                order_item=order_item,
                meal_item=meal_item_data['meal_item'],
                price_at_time=meal_item_data['price_at_time'],
                quantity=quantity
            )
    
    # Fetch order with items for response
    order_items = await OrderItem.filter(order=order).prefetch_related("menu_item", "addons", "meal_items")
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
                "price_adjustment": str(oa.price_at_time),
                "quantity": oa.quantity
            })
        meal_items = await oi.meal_items.all().prefetch_related("meal_item")
        meal_items_data = []
        for om in meal_items:
            meal_item = await om.meal_item
            meal_items_data.append({
                "id": meal_item.id,
                "name": meal_item.name,
                "price": str(om.price_at_time),
                "quantity": om.quantity
            })
        items_data.append({
            **item_dict.dict(),
            "menu_item": {
                "id": menu_item_dict.id,
                "name": menu_item_dict.name,
                "description": menu_item_dict.description
            },
            "addons": addons_data,
            "meal_items": meal_items_data,
            "meal_charge": str(oi.meal_charge) if hasattr(oi, 'meal_charge') else "0.00"
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
                    "price_adjustment": str(oa.price_at_time),
                    "quantity": oa.quantity
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
                    "price_adjustment": str(oa.price_at_time),
                    "quantity": oa.quantity
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

@router.patch("/orders/{order_id}/payment-method")
async def update_order_payment_method(
    order_id: int,
    payment_data: UpdatePaymentMethodRequest,
    user: Optional[User] = Depends(get_optional_user)
):
    """Update the payment method for an order (e.g., for cash payments)"""
    order = await Order.get_or_none(id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # If user is authenticated, verify they own the order
    if user:
        if user.role == Role.CUSTOMER and order.customer_id != user.id:
            raise HTTPException(status_code=403, detail="You don't have access to this order")
    
    if order.payment_status != PaymentStatus.PENDING:
        raise HTTPException(status_code=400, detail="Cannot change payment method for an order that is not pending payment.")

    try:
        order.payment_method = PaymentMethod(payment_data.payment_method)
        if payment_data.payment_method == PaymentMethod.CASH.value:
            # For cash, payment is considered "paid" from the customer's perspective
            # but still pending for restaurant to collect
            order.payment_status = PaymentStatus.PAID 
        await order.save()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payment method")
    
    return await Order_Pydantic.from_tortoise_orm(order)

@router.get("/orders/{order_id}/payment-status")
async def get_order_payment_status(
    order_id: int, 
    user: Optional[User] = Depends(get_optional_user)
):
    """Get the payment status of a specific order"""
    order = await Order.get_or_none(id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # If user is authenticated, verify they own the order
    if user:
        if user.role == Role.CUSTOMER and order.customer_id != user.id:
            raise HTTPException(status_code=403, detail="You don't have access to this order")
    
    return {
        "payment_status": order.payment_status.value if hasattr(order.payment_status, 'value') else str(order.payment_status),
        "payment_method": order.payment_method.value if order.payment_method and hasattr(order.payment_method, 'value') else (str(order.payment_method) if order.payment_method else None)
    }

@router.get("/restaurants/{restaurant_id}/orders/large-display")
async def get_orders_large_display(
    restaurant_id: int,
    user: User = Depends(get_current_user)
):
    """Get orders for large display screen (admin only)"""
    if user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(status_code=403, detail="Only restaurant admins can access large orders display")
    
    restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found or you don't have access")
    
    # Get orders with status: pending, confirmed, preparing, ready
    orders = await Order.filter(
        restaurant=restaurant,
        status__in=[OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PREPARING, OrderStatus.READY]
    ).prefetch_related("customer", "items").order_by("-created_at")
    
    # Sort by status priority: pending > confirmed > preparing > ready
    status_priority = {
        OrderStatus.PENDING: 1,
        OrderStatus.CONFIRMED: 2,
        OrderStatus.PREPARING: 3,
        OrderStatus.READY: 4
    }
    
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
                    "price_adjustment": str(oa.price_at_time),
                    "quantity": oa.quantity
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
            "items": items_data,
            "status_priority": status_priority.get(order.status, 99)
        })
    
    # Sort by status priority, then by creation time
    result.sort(key=lambda x: (x["status_priority"], x["created_at"]))
    
    return result

