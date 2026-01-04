import stripe
import os
from dotenv import load_dotenv
from models.platform_settings import PlatformSettings

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

async def get_platform_fee_percent():
    """Get platform fee percentage from database, create record if doesn't exist"""
    settings = await PlatformSettings.get_or_create_settings()
    return float(settings.platform_fee_percent)

async def create_express_account(email: str = None, country: str = "US"):
    """Create a Stripe Express Connected Account"""
    account_data = {
        "type": "express",
        "country": country,
        "capabilities": {
            "card_payments": {"requested": True},
            "transfers": {"requested": True},
        },
    }
    if email:
        account_data["email"] = email
    
    account = stripe.Account.create(**account_data)
    return account

async def create_account_link(account_id: str, refresh_url: str, return_url: str, type: str = "account_onboarding"):
    """Create an AccountLink for onboarding or updating a Connected Account"""
    account_link = stripe.AccountLink.create(
        account=account_id,
        refresh_url=refresh_url,
        return_url=return_url,
        type=type,
    )
    return account_link

async def create_payment_intent(amount: int, currency: str, destination_account_id: str, metadata: dict = None):
    """Create a PaymentIntent with destination (Destination Charge)"""
    platform_fee_percent = await get_platform_fee_percent()
    application_fee_amount = int(amount * platform_fee_percent / 100)
    
    payment_intent_data = {
        "amount": amount,
        "currency": currency,
        "application_fee_amount": application_fee_amount,
        "transfer_data": {
            "destination": destination_account_id,
        },
    }
    
    if metadata:
        payment_intent_data["metadata"] = metadata
    
    payment_intent = stripe.PaymentIntent.create(**payment_intent_data)
    return payment_intent

async def get_account(account_id: str):
    """Retrieve a Stripe Account"""
    return stripe.Account.retrieve(account_id)

async def handle_webhook(payload: bytes, sig_header: str):
    """Verify and parse Stripe webhook"""
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if not webhook_secret:
        raise ValueError("STRIPE_WEBHOOK_SECRET not set")
    
    event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    return event

