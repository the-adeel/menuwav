from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from decimal import Decimal

from models.receipt import Receipt, Receipt_Pydantic
from models.order import Order
from models.restaurant import Restaurant
from models.user import User, Role
from services.auth import get_current_user
from services.printer_service import list_printers, print_receipt
from services.receipt_service import generate_receipt_content

router = APIRouter()


class PrintReceiptRequest(BaseModel):
    order_id: int
    printer_name: str


@router.get("/restaurants/{restaurant_id}/printers")
async def get_printers(restaurant_id: int, user: User = Depends(get_current_user)):
    """
    Get list of available printers on the system.
    Only accessible by restaurant admins and superadmins.
    """
    # Verify user has access to restaurant
    if user.role == Role.SUPERADMIN:
        restaurant = await Restaurant.get_or_none(id=restaurant_id)
    else:
        restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    if user.role != Role.SUPERADMIN and user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(status_code=403, detail="Only restaurant admins can access printers")
    
    try:
        printers = list_printers()
        return {"printers": printers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing printers: {str(e)}")


@router.post("/restaurants/{restaurant_id}/receipts/print")
async def print_receipt_endpoint(
    restaurant_id: int,
    request: PrintReceiptRequest,
    user: User = Depends(get_current_user)
):
    """
    Print a receipt for an order and save it to the database.
    """
    # Verify user has access to restaurant
    if user.role == Role.SUPERADMIN:
        restaurant = await Restaurant.get_or_none(id=restaurant_id)
    else:
        restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    if user.role != Role.SUPERADMIN and user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(status_code=403, detail="Only restaurant admins can print receipts")
    
    # Get order and verify it belongs to restaurant
    order = await Order.get_or_none(id=request.order_id).prefetch_related("restaurant")
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order_restaurant = await order.restaurant
    if order_restaurant.id != restaurant.id:
        raise HTTPException(status_code=403, detail="Order does not belong to this restaurant")
    
    # Generate receipt content
    try:
        receipt_content = await generate_receipt_content(order)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating receipt: {str(e)}")
    
    # Print receipt
    print(f"[RECEIPT] Printing receipt for order {request.order_id} to printer {request.printer_name}")
    success, error_message = print_receipt(request.printer_name, receipt_content)
    print(f"[RECEIPT] Print result: success={success}, error={error_message}")
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to print receipt: {error_message}")
    
    # Save receipt to database
    try:
        receipt = await Receipt.create(
            restaurant=restaurant,
            order=order,
            printer_name=request.printer_name,
            receipt_data=receipt_content,
            printed_by=user
        )
        receipt_dict = await Receipt_Pydantic.from_tortoise_orm(receipt)
        return {
            "success": True,
            "message": "Receipt printed successfully",
            "receipt": receipt_dict.dict()
        }
    except Exception as e:
        # Receipt was printed but failed to save - log error but don't fail the request
        print(f"Warning: Receipt printed but failed to save to database: {str(e)}")
        return {
            "success": True,
            "message": "Receipt printed successfully (but failed to save record)",
            "warning": str(e)
        }


@router.get("/restaurants/{restaurant_id}/receipts")
async def get_receipts(
    restaurant_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(get_current_user)
):
    """
    Get all saved receipts for a restaurant with pagination.
    """
    # Verify user has access to restaurant
    if user.role == Role.SUPERADMIN:
        restaurant = await Restaurant.get_or_none(id=restaurant_id)
    else:
        restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    if user.role != Role.SUPERADMIN and user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(status_code=403, detail="Only restaurant admins can view receipts")
    
    # Get receipts with pagination
    offset = (page - 1) * limit
    receipts = await Receipt.filter(restaurant=restaurant)\
        .prefetch_related("order", "printed_by")\
        .order_by("-printed_at")\
        .offset(offset)\
        .limit(limit)\
        .all()
    
    total_count = await Receipt.filter(restaurant=restaurant).count()
    
    # Format receipts with order details
    receipts_data = []
    for receipt in receipts:
        order = await receipt.order
        printed_by_user = await receipt.printed_by
        
        receipt_dict = await Receipt_Pydantic.from_tortoise_orm(receipt)
        receipts_data.append({
            **receipt_dict.dict(),
            "order_number": order.order_number or f"#{order.id}",
            "order_total": str(order.total),
            "printed_by_username": printed_by_user.username if printed_by_user else None
        })
    
    return {
        "receipts": receipts_data,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total_count,
            "pages": (total_count + limit - 1) // limit
        }
    }


@router.get("/restaurants/{restaurant_id}/receipts/{receipt_id}")
async def get_receipt(
    restaurant_id: int,
    receipt_id: int,
    user: User = Depends(get_current_user)
):
    """
    Get a single receipt by ID with full details.
    """
    # Verify user has access to restaurant
    if user.role == Role.SUPERADMIN:
        restaurant = await Restaurant.get_or_none(id=restaurant_id)
    else:
        restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    if user.role != Role.SUPERADMIN and user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(status_code=403, detail="Only restaurant admins can view receipts")
    
    # Get receipt
    receipt = await Receipt.get_or_none(id=receipt_id).prefetch_related("order", "printed_by", "restaurant")
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    
    receipt_restaurant = await receipt.restaurant
    if receipt_restaurant.id != restaurant.id:
        raise HTTPException(status_code=403, detail="Receipt does not belong to this restaurant")
    
    # Get order details
    order = await receipt.order
    printed_by_user = await receipt.printed_by
    
    # Get order items for full details
    order_items = await order.items.all().prefetch_related("menu_item", "addons", "meal_items")
    items_data = []
    for oi in order_items:
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
            "id": oi.id,
            "menu_item": {
                "id": menu_item.id,
                "name": menu_item.name,
                "description": menu_item.description
            },
            "quantity": oi.quantity,
            "price_at_time": str(oi.price_at_time),
            "addons": addons_data,
            "meal_items": meal_items_data,
            "meal_charge": str(oi.meal_charge) if hasattr(oi, 'meal_charge') else "0.00"
        })
    
    receipt_dict = await Receipt_Pydantic.from_tortoise_orm(receipt)
    return {
        **receipt_dict.dict(),
        "order": {
            "id": order.id,
            "order_number": order.order_number or f"#{order.id}",
            "total": str(order.total),
            "status": order.status.value,
            "payment_method": order.payment_method.value if order.payment_method else None,
            "payment_status": order.payment_status.value,
            "created_at": order.created_at.isoformat() if hasattr(order.created_at, 'isoformat') else str(order.created_at),
            "customer_name": order.customer_name,
            "customer_phone": order.customer_phone,
            "table_number": order.table_number,
            "items": items_data
        },
        "printed_by_username": printed_by_user.username if printed_by_user else None
    }

