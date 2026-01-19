from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from decimal import Decimal

from models.membership_plan import MembershipPlan, MembershipPlan_Pydantic, MembershipPlanIn_Pydantic
from models.user import User, Role
from services.auth import get_current_user
from services.stripe_service import create_stripe_price

router = APIRouter()

class MembershipPlanCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: Decimal
    billing_interval: str = "month"  # "day" or "month"
    features: Dict[str, Any] = {}
    is_active: bool = True

class MembershipPlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    billing_interval: Optional[str] = None
    features: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

@router.get("/")
async def list_membership_plans(active_only: bool = True):
    """List all membership plans (public endpoint, can filter by active status)"""
    query = MembershipPlan.all()
    if active_only:
        query = query.filter(is_active=True)
    plans = await query
    return [await MembershipPlan_Pydantic.from_tortoise_orm(plan) for plan in plans]

@router.get("/{plan_id}")
async def get_membership_plan(plan_id: int):
    """Get a specific membership plan by ID"""
    plan = await MembershipPlan.get_or_none(id=plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Membership plan not found")
    return await MembershipPlan_Pydantic.from_tortoise_orm(plan)

@router.post("/", response_model=MembershipPlan_Pydantic)
async def create_membership_plan(
    plan_data: MembershipPlanCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new membership plan (superadmin only)"""
    if current_user.role != Role.SUPERADMIN:
        raise HTTPException(status_code=403, detail="Only superadmin can create membership plans")
    
    # Validate billing_interval
    if plan_data.billing_interval not in ["day", "month"]:
        raise HTTPException(status_code=400, detail="billing_interval must be 'day' or 'month'")
    
    # Validate price
    if plan_data.price < 0:
        raise HTTPException(status_code=400, detail="Price cannot be negative")
    
    # Create Stripe Price object (even for $0 plans)
    try:
        stripe_price = await create_stripe_price(
            amount=float(plan_data.price),
            currency="usd",
            interval=plan_data.billing_interval
        )
        stripe_price_id = stripe_price.id
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create Stripe price: {str(e)}")
    
    # Create plan in database
    try:
        plan = await MembershipPlan.create(
            name=plan_data.name,
            description=plan_data.description,
            price=plan_data.price,
            stripe_price_id=stripe_price_id,
            billing_interval=plan_data.billing_interval,
            features=plan_data.features,
            is_active=plan_data.is_active
        )
        return await MembershipPlan_Pydantic.from_tortoise_orm(plan)
    except Exception as e:
        # If database creation fails, we should ideally clean up Stripe price
        # But for now, just raise error
        raise HTTPException(status_code=500, detail=f"Failed to create membership plan: {str(e)}")

@router.put("/{plan_id}", response_model=MembershipPlan_Pydantic)
async def update_membership_plan(
    plan_id: int,
    plan_data: MembershipPlanUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update a membership plan (superadmin only)"""
    if current_user.role != Role.SUPERADMIN:
        raise HTTPException(status_code=403, detail="Only superadmin can update membership plans")
    
    plan = await MembershipPlan.get_or_none(id=plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Membership plan not found")
    
    # Check if price or billing_interval is changing - if so, create new Stripe Price
    price_changed = plan_data.price is not None and plan_data.price != plan.price
    interval_changed = plan_data.billing_interval is not None and plan_data.billing_interval != plan.billing_interval
    
    new_stripe_price_id = None
    if price_changed or interval_changed:
        # Validate
        new_price = plan_data.price if plan_data.price is not None else plan.price
        new_interval = plan_data.billing_interval if plan_data.billing_interval is not None else plan.billing_interval
        
        if new_price < 0:
            raise HTTPException(status_code=400, detail="Price cannot be negative")
        if new_interval not in ["day", "month"]:
            raise HTTPException(status_code=400, detail="billing_interval must be 'day' or 'month'")
        
        # Create new Stripe Price (existing subscriptions will keep old price)
        try:
            stripe_price = await create_stripe_price(
                amount=float(new_price),
                currency="usd",
                interval=new_interval
            )
            new_stripe_price_id = stripe_price.id
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create new Stripe price: {str(e)}")
    
    # Update plan
    update_dict = {}
    if plan_data.name is not None:
        update_dict["name"] = plan_data.name
    if plan_data.description is not None:
        update_dict["description"] = plan_data.description
    if plan_data.price is not None:
        update_dict["price"] = plan_data.price
    if plan_data.billing_interval is not None:
        update_dict["billing_interval"] = plan_data.billing_interval
    if plan_data.features is not None:
        update_dict["features"] = plan_data.features
    if plan_data.is_active is not None:
        update_dict["is_active"] = plan_data.is_active
    if new_stripe_price_id:
        update_dict["stripe_price_id"] = new_stripe_price_id
    
    if update_dict:
        for key, value in update_dict.items():
            setattr(plan, key, value)
        await plan.save()
    
    return await MembershipPlan_Pydantic.from_tortoise_orm(plan)

@router.delete("/{plan_id}")
async def delete_membership_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user)
):
    """Delete/deactivate a membership plan (superadmin only)"""
    if current_user.role != Role.SUPERADMIN:
        raise HTTPException(status_code=403, detail="Only superadmin can delete membership plans")
    
    plan = await MembershipPlan.get_or_none(id=plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Membership plan not found")
    
    # Soft delete by setting is_active to False
    plan.is_active = False
    await plan.save()
    
    return {"message": "Membership plan deactivated successfully"}

