from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator

class MealItem(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    price = fields.DecimalField(max_digits=10, decimal_places=2)
    image_url = fields.CharField(max_length=500, null=True)
    restaurant = fields.ForeignKeyField("models.Restaurant", related_name="meal_items")
    is_available = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        unique_together = ("name", "restaurant")

MealItem_Pydantic = pydantic_model_creator(MealItem, name="MealItem")
MealItemIn_Pydantic = pydantic_model_creator(MealItem, name="MealItemIn", exclude_readonly=True)

