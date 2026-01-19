import os
from dotenv import load_dotenv

load_dotenv()

TORTOISE_ORM = {
    "connections": {"default": os.getenv("DB_URL")},
    "apps": {
        "models": {
            "models": [
                "models.user",
                "models.restaurant",
                "models.menu",
                "models.category",
                "models.menu_item",
                "models.addon",
                "models.menu_item_addon",
                "models.ingredient",
                "models.menu_item_ingredient",
                "models.meal_item",
                "models.menu_item_meal_item",
                "models.order",
                "models.order_item",
                "models.order_item_addon",
                "models.order_meal_item",
                "models.receipt",
                "models.qr_code",
                "models.platform_settings",
                "models.generated_menu",
                "models.membership_plan",
                "models.restaurant_subscription",
                "aerich.models"
            ],
            "default_connection": "default",
        }
    },
}