from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from decimal import Decimal

from models.platform_settings import PlatformSettings, PlatformSettings_Pydantic
from models.user import User, Role
from services.auth import get_current_user

router = APIRouter()

class UpdatePlatformSettingsRequest(BaseModel):
    platform_fee_percent: float

@router.get("/platform-settings", response_model=PlatformSettings_Pydantic)
async def get_platform_settings(user: User = Depends(get_current_user)):
    """Get platform settings (superadmin only)"""
    if user.role != Role.SUPERADMIN:
        raise HTTPException(status_code=403, detail="Only superadmin can view platform settings")
    
    settings = await PlatformSettings.get_or_create_settings()
    return await PlatformSettings_Pydantic.from_tortoise_orm(settings)

@router.patch("/platform-settings", response_model=PlatformSettings_Pydantic)
async def update_platform_settings(
    request: UpdatePlatformSettingsRequest,
    user: User = Depends(get_current_user)
):
    """Update platform settings (superadmin only)"""
    if user.role != Role.SUPERADMIN:
        raise HTTPException(status_code=403, detail="Only superadmin can update platform settings")
    
    # Validate fee percentage range (0-100)
    if request.platform_fee_percent < 0 or request.platform_fee_percent > 100:
        raise HTTPException(
            status_code=400,
            detail="platform_fee_percent must be between 0 and 100"
        )
    
    settings = await PlatformSettings.get_or_create_settings()
    settings.platform_fee_percent = Decimal(str(request.platform_fee_percent))
    await settings.save()
    
    return await PlatformSettings_Pydantic.from_tortoise_orm(settings)

