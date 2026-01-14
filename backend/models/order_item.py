from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator

class OrderItem(Model):
    id = fields.IntField(pk=True)
    order = fields.ForeignKeyField("models.Order", related_name="items")
    menu_item = fields.ForeignKeyField("models.MenuItem", related_name="order_items")
    quantity = fields.IntField(default=1)
    price_at_time = fields.DecimalField(max_digits=10, decimal_places=2)
    meal_charge = fields.DecimalField(max_digits=10, decimal_places=2, default=0.00)

OrderItem_Pydantic = pydantic_model_creator(OrderItem, name="OrderItem")
OrderItemIn_Pydantic = pydantic_model_creator(OrderItem, name="OrderItemIn", exclude_readonly=True)

