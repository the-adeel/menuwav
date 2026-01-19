# seed_membership_plans.py
import asyncio
import sys
import os
from decimal import Decimal

script_dir = os.path.dirname(os.path.realpath(__file__))
backend_dir = os.path.dirname(script_dir)  # Go up one level to backend/
sys.path.insert(0, backend_dir)

from dotenv import load_dotenv

from models.membership_plan import MembershipPlan
from tortoise import Tortoise
from helpers.tortoise_config import TORTOISE_ORM
from services.stripe_service import create_stripe_price

load_dotenv()

# Define the 3 membership plans
PLANS = [
    {
        "name": "Free",
        "description": "Perfect for getting started with basic features",
        "price": Decimal('0.00'),
        "billing_interval": "month",
        "is_active": True,
        "features": {
            "max_menus": 1,
            "max_menu_items": 20,
            "qr_codes": True,
            "analytics": False,
            "custom_domain": False,
            "priority_support": False,
            "email_support": False,
            "api_access": False
        }
    },
    {
        "name": "Basic",
        "description": "Ideal for small restaurants with moderate traffic",
        "price": Decimal('29.99'),
        "billing_interval": "month",
        "is_active": True,
        "features": {
            "max_menus": 3,
            "max_menu_items": 100,
            "qr_codes": True,
            "analytics": True,
            "custom_domain": False,
            "priority_support": False,
            "email_support": True,
            "api_access": False
        }
    },
    {
        "name": "Premium",
        "description": "Everything you need for a thriving restaurant business",
        "price": Decimal('99.99'),
        "billing_interval": "month",
        "is_active": True,
        "features": {
            "max_menus": -1,  # -1 means unlimited
            "max_menu_items": -1,  # -1 means unlimited
            "qr_codes": True,
            "analytics": True,
            "custom_domain": True,
            "priority_support": True,
            "email_support": True,
            "api_access": True
        }
    }
]

async def init():
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas(safe=True)

    print("Starting membership plans seeding...")
    print("=" * 60)

    for plan_data in PLANS:
        plan_name = plan_data["name"]
        
        # Check if plan already exists
        existing_plan = await MembershipPlan.get_or_none(name=plan_name)
        
        if existing_plan:
            print(f"\n[WARNING] Plan '{plan_name}' already exists!")
            print(f"   Skipping... (to update, use admin panel or delete and re-run)")
            continue

        try:
            print(f"\n[INFO] Creating plan: {plan_name}")
            
            # Create Stripe Price object
            print(f"   Creating Stripe Price for ${plan_data['price']}/{plan_data['billing_interval']}...")
            stripe_price = await create_stripe_price(
                amount=float(plan_data["price"]),
                currency="usd",
                interval=plan_data["billing_interval"]
            )
            print(f"   [SUCCESS] Stripe Price created: {stripe_price.id}")
            
            # Create plan in database
            plan = await MembershipPlan.create(
                name=plan_data["name"],
                description=plan_data["description"],
                price=plan_data["price"],
                stripe_price_id=stripe_price.id,
                billing_interval=plan_data["billing_interval"],
                features=plan_data["features"],
                is_active=plan_data["is_active"]
            )
            
            print(f"   [SUCCESS] Plan '{plan_name}' created successfully!")
            print(f"   Features: {len(plan_data['features'])} features configured")
            
        except Exception as e:
            print(f"   [ERROR] Error creating plan '{plan_name}': {str(e)}")
            import traceback
            traceback.print_exc()
            continue

    print("\n" + "=" * 60)
    print("[SUCCESS] Membership plans seeding completed!")
    print("\nSummary:")
    
    all_plans = await MembershipPlan.all()
    for plan in all_plans:
        print(f"  • {plan.name}: ${plan.price}/{plan.billing_interval} - {'Active' if plan.is_active else 'Inactive'}")
    
    await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(init())

