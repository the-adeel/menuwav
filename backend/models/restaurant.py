from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator

class Restaurant(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    owner = fields.ForeignKeyField("models.User", related_name="restaurants")
    is_approved = fields.BooleanField(default=False)
    address = fields.TextField(null=True)
    phone = fields.CharField(max_length=20, null=True)
    email = fields.CharField(max_length=255, null=True)

Restaurant_Pydantic = pydantic_model_creator(Restaurant, name="Restaurant")
RestaurantIn_Pydantic = pydantic_model_creator(Restaurant, name="RestaurantIn", exclude_readonly=True)