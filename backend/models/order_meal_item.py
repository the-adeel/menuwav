from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator

class OrderMealItem(Model):
    id = fields.IntField(pk=True)
    order_item = fields.ForeignKeyField("models.OrderItem", related_name="meal_items")
    meal_item = fields.ForeignKeyField("models.MealItem", related_name="order_meal_items")
    price_at_time = fields.DecimalField(max_digits=10, decimal_places=2)
    quantity = fields.IntField(default=1)

OrderMealItem_Pydantic = pydantic_model_creator(OrderMealItem, name="OrderMealItem")
OrderMealItemIn_Pydantic = pydantic_model_creator(OrderMealItem, name="OrderMealItemIn", exclude_readonly=True)

