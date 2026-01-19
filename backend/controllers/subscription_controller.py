from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import os

from models.restaurant import Restaurant
from models.restaurant_subscription import RestaurantSubscription, SubscriptionStatus
from models.membership_plan import MembershipPlan
from models.user import User, Role
from services.auth import get_current_user
from services.stripe_service import (
    create_or_get_stripe_customer,
    create_checkout_session_for_subscription,
    create_subscription_directly,
    create_customer_portal_session
)
from datetime import datetime, timezone

router = APIRouter()

class CheckoutSessionResponse(BaseModel):
    checkout_url: str
    session_id: str

class SubscriptionResponse(BaseModel):
    id: int
    plan_name: str
    plan_price: float
    status: str
    current_period_start: datetime
    current_period_end: datetime

@router.post("/create-checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    plan_id: int,
    restaurant_id: int,
    user: User = Depends(get_current_user)
):
    """Create Stripe Checkout Session for subscription (works for both $0 and paid plans)"""
    if user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(status_code=403, detail="Only restaurant admins can create checkout sessions")
    
    restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found or you don't have access")
    
    plan = await MembershipPlan.get_or_none(id=plan_id, is_active=True)
    if not plan:
        raise HTTPException(status_code=404, detail="Membership plan not found or inactive")
    
    # Get or create Stripe Customer
    if not restaurant.stripe_customer_id:
        customer_email = restaurant.email
        stripe_customer = await create_or_get_stripe_customer(
            email=customer_email,
            metadata={"restaurant_id": str(restaurant.id)}
        )
        restaurant.stripe_customer_id = stripe_customer.id
        await restaurant.save()
    else:
        stripe_customer_id = restaurant.stripe_customer_id
    
    # Create checkout session
    base_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    success_url = f"{base_url}/subscription/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{base_url}/restaurant-admin?section=subscription"
    
    checkout_session = await create_checkout_session_for_subscription(
        customer_id=restaurant.stripe_customer_id,
        price_id=plan.stripe_price_id,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"restaurant_id": str(restaurant.id), "plan_id": str(plan.id)}
    )
    
    return CheckoutSessionResponse(
        checkout_url=checkout_session.url,
        session_id=checkout_session.id
    )

@router.get("/restaurant/{restaurant_id}", response_model=SubscriptionResponse)
async def get_restaurant_subscription(
    restaurant_id: int,
    user: User = Depends(get_current_user)
):
    """Get restaurant's current subscription"""
    if user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(status_code=403, detail="Only restaurant admins can view subscriptions")
    
    restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found or you don't have access")
    
    subscription = await RestaurantSubscription.get_or_none(restaurant=restaurant)
    if not subscription:
        raise HTTPException(status_code=404, detail="No subscription found for this restaurant")
    
    plan = await subscription.plan
    return SubscriptionResponse(
        id=subscription.id,
        plan_name=plan.name,
        plan_price=float(plan.price),
        status=subscription.status.value if hasattr(subscription.status, 'value') else str(subscription.status),
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end
    )

@router.post("/cancel")
async def cancel_subscription(
    restaurant_id: int,
    user: User = Depends(get_current_user)
):
    """Cancel subscription (sets cancel_at_period_end)"""
    if user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(status_code=403, detail="Only restaurant admins can cancel subscriptions")
    
    restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found or you don't have access")
    
    subscription = await RestaurantSubscription.get_or_none(restaurant=restaurant)
    if not subscription:
        raise HTTPException(status_code=404, detail="No subscription found")
    
    # Cancel via Stripe API
    import stripe
    try:
        stripe_subscription = stripe.Subscription.modify(
            subscription.stripe_subscription_id,
            cancel_at_period_end=True
        )
        subscription.cancel_at_period_end = True
        await subscription.save()
        return {"message": "Subscription will be canceled at the end of the current period"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel subscription: {str(e)}")

@router.get("/portal")
async def get_customer_portal_link(
    restaurant_id: int,
    user: User = Depends(get_current_user)
):
    """Get Stripe Customer Portal link for subscription management"""
    if user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(status_code=403, detail="Only restaurant admins can access portal")
    
    restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found or you don't have access")
    
    if not restaurant.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No Stripe customer found for this restaurant")
    
    base_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    return_url = f"{base_url}/restaurant-admin?section=subscription"
    
    portal_session = await create_customer_portal_session(
        customer_id=restaurant.stripe_customer_id,
        return_url=return_url
    )
    
    return {"portal_url": portal_session.url}

