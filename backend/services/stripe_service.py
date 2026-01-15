import stripe
import os
import time
from dotenv import load_dotenv
from models.platform_settings import PlatformSettings

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

def is_test_mode():
    """Check if Stripe is in test mode"""
    api_key = os.getenv("STRIPE_SECRET_KEY", "")
    return api_key.startswith("sk_test_")

async def get_platform_fee_percent():
    """Get platform fee percentage from database, create record if doesn't exist"""
    settings = await PlatformSettings.get_or_create_settings()
    return float(settings.platform_fee_percent)

async def create_express_account(email: str = None, country: str = "US"):
    """Create a Stripe Express Connected Account"""
    if not stripe.api_key:
        raise ValueError("STRIPE_SECRET_KEY is not set in environment variables")
    
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
    
    # In test mode, pre-fill basic fields during account creation using Stripe test tokens
    # Reference: https://docs.stripe.com/connect/testing
    # Note: Some fields cannot be pre-filled for Express accounts:
    # - tos_acceptance: Must be accepted by user during onboarding (Stripe requirement)
    # - business_profile.url: May cause validation errors if not a real URL
    # We use Stripe's test tokens to ensure successful verification during testing
    if is_test_mode():
        account_data.update({
            "business_type": "individual",  # Simplest business type for testing
            "individual": {
                "email": email or "test@example.com",
                "first_name": "Test",
                "last_name": "User",
                # Use Stripe test phone number for successful validation
                # Reference: https://docs.stripe.com/connect/testing#test-phone-number-validation
                "phone": "0000000000",
                # Use Stripe test DOB for successful date of birth match
                # 1901-01-01 = Successful date of birth match
                # Reference: https://docs.stripe.com/connect/testing#test-dates-of-birth
                "dob": {
                    "day": 1,
                    "month": 1,
                    "year": 1901,
                },
                # Use Stripe test address token for successful address match
                # address_full_match = Successful address match
                # Reference: https://docs.stripe.com/connect/testing#test-addresses
                "address": {
                    "line1": "address_full_match",
                    "city": "San Francisco",
                    "state": "CA",
                    "postal_code": "94111",
                    "country": "US",
                },
                # Use Stripe test SSN last 4 for successful ID verification
                # 0000 = Successful SSN last 4 verification
                # Reference: https://docs.stripe.com/connect/testing#test-personal-id-numbers
                "ssn_last_4": "0000",
            },
        })
    
    try:
        account = stripe.Account.create(**account_data)
        return account
    except Exception as e:
        error_msg = str(e)
        if hasattr(e, 'user_message'):
            error_msg = e.user_message
        # Also check for code attribute which often has more specific error info
        if hasattr(e, 'code'):
            error_msg = f"{error_msg} (code: {e.code})"
        raise ValueError(f"Stripe API error: {error_msg}")

async def create_account_link(account_id: str, refresh_url: str, return_url: str, type: str = "account_onboarding"):
    """Create an AccountLink for onboarding or updating a Connected Account"""
    if not stripe.api_key:
        raise ValueError("STRIPE_SECRET_KEY is not set in environment variables")
    
    try:
        account_link = stripe.AccountLink.create(
            account=account_id,
            refresh_url=refresh_url,
            return_url=return_url,
            type=type,
        )
        return account_link
    except Exception as e:
        error_msg = str(e)
        if hasattr(e, 'user_message'):
            error_msg = e.user_message
        raise ValueError(f"Stripe API error: {error_msg}")

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

async def delete_account(account_id: str):
    """Delete a Stripe Express Connected Account"""
    # Only allow deletion in test mode for safety
    if not is_test_mode():
        raise ValueError("Account deletion is only allowed in test mode")
    
    account = stripe.Account.delete(account_id)
    return account

async def create_login_link(account_id: str):
    """Create a login link for a connected Express account to access their dashboard"""
    if not stripe.api_key:
        raise ValueError("STRIPE_SECRET_KEY is not set in environment variables")
    
    try:
        # Create a login link for the connected account
        # Reference: https://docs.stripe.com/api/account/login_link
        # The account_id is the connected account ID (acct_xxx)
        login_link = stripe.Account.create_login_link(
            account_id
        )
        return login_link
    except stripe.error.StripeError as e:
        error_msg = str(e)
        if hasattr(e, 'user_message'):
            error_msg = e.user_message
        if hasattr(e, 'code'):
            error_msg = f"{error_msg} (code: {e.code})"
        raise ValueError(f"Stripe API error: {error_msg}")
    except Exception as e:
        error_msg = str(e)
        if hasattr(e, 'user_message'):
            error_msg = e.user_message
        raise ValueError(f"Failed to create login link: {error_msg}")

async def handle_webhook(payload: bytes, sig_header: str):
    """Verify and parse Stripe webhook"""
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if not webhook_secret:
        raise ValueError("STRIPE_WEBHOOK_SECRET not set")
    
    event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    return event
