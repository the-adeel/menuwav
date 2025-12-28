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
                "models.menu_item",
                "models.menu_item_addon",
                "models.order",
                "models.order_item",
                "models.order_item_addon",
                "models.qr_code",
                "aerich.models"
            ],
            "default_connection": "default",
        }
    },
}