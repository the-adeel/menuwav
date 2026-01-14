from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List
from pydantic import BaseModel

from models.restaurant import Restaurant
from models.qr_code import QRCode, QRCode_Pydantic, QRType
from models.user import User, Role
from services.auth import get_current_user
from helpers.url_helpers import get_frontend_url

router = APIRouter()

class GenerateTableQRRequest(BaseModel):
    number_of_tables: int

@router.post("/{restaurant_id}/qr/generate-table")
async def generate_table_qr(restaurant_id: int, request: GenerateTableQRRequest, user: User = Depends(get_current_user)):
    if user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(status_code=403, detail="Only restaurant admins can generate QR codes")
    
    restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found or you don't have access")
    
    if request.number_of_tables < 1:
        raise HTTPException(status_code=400, detail="Number of tables must be at least 1")
    
    qr_codes = []
    base_url = get_frontend_url()
    
    for table_num in range(1, request.number_of_tables + 1):
        qr_url = f"{base_url}/menu/{restaurant_id}?table={table_num}"
        qr_code = await QRCode.create(
            restaurant=restaurant,
            table_number=table_num,
            qr_type=QRType.TABLE,
            qr_data=qr_url
        )
        qr_codes.append(await QRCode_Pydantic.from_tortoise_orm(qr_code))
    
    return qr_codes

@router.post("/{restaurant_id}/qr/generate-restaurant")
async def generate_restaurant_qr(restaurant_id: int, user: User = Depends(get_current_user)):
    if user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(status_code=403, detail="Only restaurant admins can generate QR codes")
    
    restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found or you don't have access")
    
    # Check if restaurant QR already exists
    existing_qr = await QRCode.get_or_none(restaurant=restaurant, qr_type=QRType.RESTAURANT)
    if existing_qr:
        return await QRCode_Pydantic.from_tortoise_orm(existing_qr)
    
    base_url = get_frontend_url()
    qr_url = f"{base_url}/menu/{restaurant_id}"
    
    qr_code = await QRCode.create(
        restaurant=restaurant,
        table_number=None,
        qr_type=QRType.RESTAURANT,
        qr_data=qr_url
    )
    
    return await QRCode_Pydantic.from_tortoise_orm(qr_code)

@router.get("/{restaurant_id}/qr/list", response_model=List[QRCode_Pydantic])
async def list_qr_codes(restaurant_id: int, user: User = Depends(get_current_user)):
    if user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(status_code=403, detail="Only restaurant admins can view QR codes")

    restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found or you don't have access")

    qr_codes = await QRCode.filter(restaurant=restaurant).order_by("-created_at")
    return [await QRCode_Pydantic.from_tortoise_orm(qr) for qr in qr_codes]

@router.delete("/{restaurant_id}/qr/{qr_id}")
async def delete_qr_code(restaurant_id: int, qr_id: int, user: User = Depends(get_current_user)):
    if user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(status_code=403, detail="Only restaurant admins can delete QR codes")

    restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found or you don't have access")

    qr_code = await QRCode.get_or_none(id=qr_id, restaurant=restaurant)
    if not qr_code:
        raise HTTPException(status_code=404, detail="QR code not found")

    await qr_code.delete()
    return {"message": "QR code deleted successfully"}

class BulkDeleteQRRequest(BaseModel):
    qr_ids: List[int]

@router.post("/{restaurant_id}/qr/bulk-delete")
async def bulk_delete_qr_codes(restaurant_id: int, request: BulkDeleteQRRequest, user: User = Depends(get_current_user)):
    """Bulk delete QR codes (admin only)"""
    if user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(status_code=403, detail="Only restaurant admins can delete QR codes")

    restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found or you don't have access")

    if not request.qr_ids:
        raise HTTPException(status_code=400, detail="No QR code IDs provided")

    # Get QR codes that belong to this restaurant
    qr_codes = await QRCode.filter(id__in=request.qr_ids, restaurant=restaurant).all()
    
    if not qr_codes:
        raise HTTPException(status_code=404, detail="No QR codes found")

    deleted_count = len(qr_codes)
    for qr_code in qr_codes:
        await qr_code.delete()

    return {
        "message": f"{deleted_count} QR code(s) deleted successfully",
        "deleted_count": deleted_count
    }

