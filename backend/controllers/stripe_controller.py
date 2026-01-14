from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
import os
from dotenv import load_dotenv

from models.restaurant import Restaurant
from models.order import Order
from models.user import User, Role
from services.auth import get_current_user
from services.stripe_service import (
    create_express_account,
    create_account_link,
    create_payment_intent,
    get_account,
    handle_webhook,
)
from helpers.url_helpers import get_frontend_url

load_dotenv()

router = APIRouter()

class OnboardResponse(BaseModel):
    account_link_url: str

class PaymentIntentResponse(BaseModel):
    client_secret: str

@router.post("/restaurants/{restaurant_id}/stripe/onboard", response_model=OnboardResponse)
async def initiate_onboarding(
    restaurant_id: int,
    user: User = Depends(get_current_user)
):
    """Initiate Stripe Connect onboarding for a restaurant"""
    if user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(status_code=403, detail="Only restaurant admins can initiate onboarding")
    
    restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found or you don't have access")
    
    # Get base URL from environment or use default
    base_url = get_frontend_url()
    refresh_url = f"{base_url}/restaurant-admin?section=payments&onboard=refresh"
    return_url = f"{base_url}/restaurant-admin?section=payments&onboard=success"
    
    # Create Express account if doesn't exist
    if not restaurant.stripe_account_id:
        account = await create_express_account(email=restaurant.email)
        restaurant.stripe_account_id = account.id
        await restaurant.save()
    
    # Create account link
    account_link = await create_account_link(
        account_id=restaurant.stripe_account_id,
        refresh_url=refresh_url,
        return_url=return_url,
        type="account_onboarding" if not restaurant.stripe_onboarding_complete else "account_update"
    )
    
    return OnboardResponse(account_link_url=account_link.url)

@router.get("/restaurants/{restaurant_id}/stripe/status")
async def get_stripe_status(
    restaurant_id: int,
    user: User = Depends(get_current_user)
):
    """Get Stripe connection status for a restaurant"""
    if user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(status_code=403, detail="Only restaurant admins can view status")
    
    restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found or you don't have access")
    
    return {
        "stripe_account_id": restaurant.stripe_account_id,
        "stripe_onboarding_complete": restaurant.stripe_onboarding_complete,
        "has_stripe_account": restaurant.stripe_account_id is not None
    }

@router.post("/orders/{order_id}/create-payment-intent", response_model=PaymentIntentResponse)
async def create_order_payment_intent(
    order_id: int,
    user: Optional[User] = Depends(get_current_user)
):
    """Create a payment intent for an order"""
    order = await Order.get_or_none(id=order_id).prefetch_related("restaurant")
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    restaurant = await order.restaurant
    if not restaurant.stripe_account_id or not restaurant.stripe_onboarding_complete:
        raise HTTPException(
            status_code=400,
            detail="Restaurant has not completed Stripe onboarding"
        )
    
    from models.order import PaymentStatus
    payment_status_value = order.payment_status.value if hasattr(order.payment_status, 'value') else str(order.payment_status)
    if payment_status_value != PaymentStatus.PENDING.value:
        raise HTTPException(
            status_code=400,
            detail=f"Order payment status is {order.payment_status}, cannot create payment intent"
        )
    
    # Convert total to cents
    amount_cents = int(float(order.total) * 100)
    
    # Create payment intent
    payment_intent = await create_payment_intent(
        amount=amount_cents,
        currency="usd",
        destination_account_id=restaurant.stripe_account_id,
        metadata={
            "order_id": str(order.id),
            "restaurant_id": str(restaurant.id),
        }
    )
    
    # Save payment intent ID to order
    order.stripe_payment_intent_id = payment_intent.id
    await order.save()
    
    return PaymentIntentResponse(client_secret=payment_intent.client_secret)

@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks"""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")
    
    try:
        event = await handle_webhook(payload, sig_header)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook signature verification failed: {str(e)}")
    
    # Handle different event types
    if event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        order_id = payment_intent.get("metadata", {}).get("order_id")
        if order_id:
            order = await Order.get_or_none(id=int(order_id))
            if order:
                from models.order import PaymentStatus, PaymentMethod
                order.payment_status = PaymentStatus.PAID
                order.payment_method = PaymentMethod.ONLINE
                await order.save()
    
    elif event["type"] == "payment_intent.payment_failed":
        payment_intent = event["data"]["object"]
        order_id = payment_intent.get("metadata", {}).get("order_id")
        if order_id:
            order = await Order.get_or_none(id=int(order_id))
            if order:
                from models.order import PaymentStatus
                order.payment_status = PaymentStatus.FAILED
                await order.save()
    
    elif event["type"] == "account.updated":
        account = event["data"]["object"]
        account_id = account.get("id")
        if account_id:
            restaurant = await Restaurant.get_or_none(stripe_account_id=account_id)
            if restaurant:
                # Check if account is fully onboarded
                details_submitted = account.get("details_submitted", False)
                charges_enabled = account.get("charges_enabled", False)
                restaurant.stripe_onboarding_complete = details_submitted and charges_enabled
                await restaurant.save()
    
    return {"status": "success"}

