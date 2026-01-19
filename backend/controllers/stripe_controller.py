from fastapi import APIRouter, Depends, HTTPException, Request
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import Optional
import os
from dotenv import load_dotenv

from models.restaurant import Restaurant
from models.order import Order
from models.user import User, Role
from models.restaurant_subscription import RestaurantSubscription, SubscriptionStatus
from models.membership_plan import MembershipPlan
from services.auth import get_current_user, get_optional_user
from services.stripe_service import (
    create_express_account,
    create_account_link,
    create_payment_intent,
    get_account,
    handle_webhook,
    delete_account,
    is_test_mode,
    create_login_link,
)

load_dotenv()

router = APIRouter()

class OnboardResponse(BaseModel):
    account_link_url: str

class PaymentIntentResponse(BaseModel):
    client_secret: str

class LoginLinkResponse(BaseModel):
    login_url: str
    expires_at: Optional[int] = None

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
    base_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    refresh_url = f"{base_url}/restaurant-admin?section=payments&onboard=refresh"
    return_url = f"{base_url}/restaurant-admin?section=payments&onboard=success"
    
    try:
        # Create Express account if doesn't exist
        if not restaurant.stripe_account_id:
            print(f"Creating Stripe Express account for restaurant {restaurant_id}")
            account = await create_express_account(email=restaurant.email)
            restaurant.stripe_account_id = account.id
            await restaurant.save()
            print(f"Created Stripe account: {account.id}")
        
        # Create account link
        print(f"Creating account link for Stripe account: {restaurant.stripe_account_id}")
        account_link = await create_account_link(
            account_id=restaurant.stripe_account_id,
            refresh_url=refresh_url,
            return_url=return_url,
            type="account_onboarding" if not restaurant.stripe_onboarding_complete else "account_update"
        )
        print(f"Created account link: {account_link.url}")
        
        return OnboardResponse(account_link_url=account_link.url)
    except ValueError as e:
        print(f"ValueError in initiate_onboarding: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        import traceback
        print(f"Exception in initiate_onboarding: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to create Stripe account link: {str(e)}")

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
    
    # If account exists, check Stripe directly to get real-time status
    # This ensures immediate updates even if webhooks haven't fired yet
    if restaurant.stripe_account_id:
        try:
            account = await get_account(restaurant.stripe_account_id)
            # Check if account is fully onboarded based on Stripe's actual status
            details_submitted = account.get("details_submitted", False)
            charges_enabled = account.get("charges_enabled", False)
            is_complete = details_submitted and charges_enabled
            
            # Update database if status changed
            if restaurant.stripe_onboarding_complete != is_complete:
                restaurant.stripe_onboarding_complete = is_complete
                await restaurant.save()
                print(f"Updated Stripe onboarding status for restaurant {restaurant_id}: {is_complete}")
        except Exception as e:
            print(f"Error checking Stripe account status: {e}")
            # Continue with database value if Stripe check fails
    
    return {
        "stripe_account_id": restaurant.stripe_account_id,
        "stripe_onboarding_complete": restaurant.stripe_onboarding_complete,
        "has_stripe_account": restaurant.stripe_account_id is not None
    }

@router.get("/restaurants/{restaurant_id}/stripe/login-link", response_model=LoginLinkResponse)
async def get_restaurant_login_link(
    restaurant_id: int,
    user: User = Depends(get_current_user)
):
    """Get a login link for restaurant to access their Stripe Express dashboard"""
    if user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(status_code=403, detail="Only restaurant admins can access")
    
    restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found or you don't have access")
    
    if not restaurant.stripe_account_id:
        raise HTTPException(status_code=400, detail="No Stripe account connected")
    
    if not restaurant.stripe_onboarding_complete:
        raise HTTPException(
            status_code=400, 
            detail="Stripe account onboarding not complete. Please complete onboarding first."
        )
    
    try:
        login_link = await create_login_link(restaurant.stripe_account_id)
        
        # Stripe login link object - access attributes using dot notation
        # Stripe Python SDK returns objects with attribute access
        try:
            login_url = login_link.url
            expires_at = getattr(login_link, 'expires_at', None)
        except AttributeError:
            # Fallback: try dict access if it's a dict-like object
            login_url = login_link.get('url') if hasattr(login_link, 'get') else None
            expires_at = login_link.get('expires_at') if hasattr(login_link, 'get') else None
        
        if not login_url:
            raise HTTPException(status_code=500, detail="Failed to get login URL from Stripe response")
        
        return LoginLinkResponse(
            login_url=login_url,
            expires_at=expires_at
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        import traceback
        print(f"Error creating login link: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to create login link: {str(e)}")

@router.delete("/restaurants/{restaurant_id}/stripe/disconnect")
async def disconnect_stripe(
    restaurant_id: int,
    user: User = Depends(get_current_user)
):
    """Disconnect Stripe account from restaurant"""
    if user.role != Role.RESTAURANT_ADMIN:
        raise HTTPException(status_code=403, detail="Only restaurant admins can disconnect Stripe")
    
    restaurant = await Restaurant.get_or_none(id=restaurant_id, owner=user)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found or you don't have access")
    
    if not restaurant.stripe_account_id:
        raise HTTPException(status_code=400, detail="No Stripe account connected")
    
    # Delete the Stripe account if in test mode (safe to do)
    # In live mode, we just clear our records but leave the Stripe account
    if is_test_mode():
        try:
            await delete_account(restaurant.stripe_account_id)
        except Exception as e:
            # Log error but continue - we'll still clear our records
            print(f"Warning: Could not delete Stripe account: {e}")
    
    # Clear the connection from our database
    restaurant.stripe_account_id = None
    restaurant.stripe_onboarding_complete = False
    await restaurant.save()
    
    return {"status": "success", "message": "Stripe account disconnected successfully"}

@router.post("/orders/{order_id}/create-payment-intent", response_model=PaymentIntentResponse)
async def create_order_payment_intent(
    order_id: int,
    user: Optional[User] = Depends(get_optional_user)
):
    """Create a payment intent for an order. Works for both authenticated and guest users."""
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
    
    # Subscription webhook handlers
    elif event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        if session.get("mode") == "subscription":
            # Get metadata
            metadata = session.get("metadata", {})
            restaurant_id = metadata.get("restaurant_id")
            plan_id = metadata.get("plan_id")
            customer_id = session.get("customer")
            
            if restaurant_id and plan_id:
                restaurant = await Restaurant.get_or_none(id=int(restaurant_id))
                plan = await MembershipPlan.get_or_none(id=int(plan_id))
                
                if restaurant and plan and customer_id:
                    # Update or create subscription
                    subscription_id = session.get("subscription")
                    if subscription_id:
                        # Get subscription details from Stripe
                        import stripe
                        stripe_subscription = stripe.Subscription.retrieve(subscription_id)
                        
                        subscription = await RestaurantSubscription.get_or_none(restaurant=restaurant)
                        if subscription:
                            # Update existing
                            subscription.stripe_subscription_id = stripe_subscription.id
                            subscription.plan = plan
                            subscription.status = SubscriptionStatus.ACTIVE
                            subscription.current_period_start = datetime.fromtimestamp(stripe_subscription.current_period_start, tz=timezone.utc)
                            subscription.current_period_end = datetime.fromtimestamp(stripe_subscription.current_period_end, tz=timezone.utc)
                            await subscription.save()
                        else:
                            # Create new
                            subscription = await RestaurantSubscription.create(
                                restaurant=restaurant,
                                plan=plan,
                                stripe_subscription_id=stripe_subscription.id,
                                status=SubscriptionStatus.ACTIVE,
                                current_period_start=datetime.fromtimestamp(stripe_subscription.current_period_start, tz=timezone.utc),
                                current_period_end=datetime.fromtimestamp(stripe_subscription.current_period_end, tz=timezone.utc),
                                cancel_at_period_end=False
                            )
    
    elif event["type"] == "customer.subscription.created":
        stripe_subscription = event["data"]["object"]
        subscription_id = stripe_subscription.get("id")
        
        # Find subscription by stripe_subscription_id
        subscription = await RestaurantSubscription.get_or_none(stripe_subscription_id=subscription_id)
        if subscription:
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.current_period_start = datetime.fromtimestamp(stripe_subscription.get("current_period_start"), tz=timezone.utc)
            subscription.current_period_end = datetime.fromtimestamp(stripe_subscription.get("current_period_end"), tz=timezone.utc)
            await subscription.save()
    
    elif event["type"] == "customer.subscription.updated":
        stripe_subscription = event["data"]["object"]
        subscription_id = stripe_subscription.get("id")
        
        subscription = await RestaurantSubscription.get_or_none(stripe_subscription_id=subscription_id)
        if subscription:
            status_map = {
                "active": SubscriptionStatus.ACTIVE,
                "canceled": SubscriptionStatus.CANCELED,
                "past_due": SubscriptionStatus.PAST_DUE,
                "trialing": SubscriptionStatus.TRIALING,
            }
            stripe_status = stripe_subscription.get("status")
            subscription.status = status_map.get(stripe_status, SubscriptionStatus.ACTIVE)
            subscription.current_period_start = datetime.fromtimestamp(stripe_subscription.get("current_period_start"), tz=timezone.utc)
            subscription.current_period_end = datetime.fromtimestamp(stripe_subscription.get("current_period_end"), tz=timezone.utc)
            subscription.cancel_at_period_end = stripe_subscription.get("cancel_at_period_end", False)
            await subscription.save()
    
    elif event["type"] == "customer.subscription.deleted":
        stripe_subscription = event["data"]["object"]
        subscription_id = stripe_subscription.get("id")
        
        subscription = await RestaurantSubscription.get_or_none(stripe_subscription_id=subscription_id)
        if subscription:
            subscription.status = SubscriptionStatus.CANCELED
            await subscription.save()
    
    elif event["type"] == "invoice.payment_succeeded":
        invoice = event["data"]["object"]
        subscription_id = invoice.get("subscription")
        
        if subscription_id:
            subscription = await RestaurantSubscription.get_or_none(stripe_subscription_id=subscription_id)
            if subscription:
                # Update period dates if subscription was renewed
                import stripe
                stripe_subscription = stripe.Subscription.retrieve(subscription_id)
                subscription.current_period_start = datetime.fromtimestamp(stripe_subscription.current_period_start, tz=timezone.utc)
                subscription.current_period_end = datetime.fromtimestamp(stripe_subscription.current_period_end, tz=timezone.utc)
                subscription.status = SubscriptionStatus.ACTIVE
                await subscription.save()
    
    elif event["type"] == "invoice.payment_failed":
        invoice = event["data"]["object"]
        subscription_id = invoice.get("subscription")
        
        if subscription_id:
            subscription = await RestaurantSubscription.get_or_none(stripe_subscription_id=subscription_id)
            if subscription:
                subscription.status = SubscriptionStatus.PAST_DUE
                await subscription.save()
    
    return {"status": "success"}

