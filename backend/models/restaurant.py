from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator

class Restaurant(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    subdomain = fields.CharField(max_length=100, unique=True, null=True)
    owner = fields.ForeignKeyField("models.User", related_name="restaurants")
    is_approved = fields.BooleanField(default=False)
    address = fields.TextField(null=True)
    phone = fields.CharField(max_length=20, null=True)
    email = fields.CharField(max_length=255, null=True)
    stripe_account_id = fields.CharField(max_length=255, null=True)
    stripe_onboarding_complete = fields.BooleanField(default=False)
    meal_charge = fields.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    cover_photo_url = fields.CharField(max_length=500, null=True)
    logo_url = fields.CharField(max_length=500, null=True)
    stripe_customer_id = fields.CharField(max_length=255, null=True)  # Stripe Customer ID for subscriptions

Restaurant_Pydantic = pydantic_model_creator(Restaurant, name="Restaurant")
RestaurantIn_Pydantic = pydantic_model_creator(Restaurant, name="RestaurantIn", exclude_readonly=True)