from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator

class OrderItemAddon(Model):
    id = fields.IntField(pk=True)
    order_item = fields.ForeignKeyField("models.OrderItem", related_name="addons")
    addon = fields.ForeignKeyField("models.MenuItemAddon", related_name="order_item_addons")
    price_at_time = fields.DecimalField(max_digits=10, decimal_places=2)
    quantity = fields.IntField(default=1)

OrderItemAddon_Pydantic = pydantic_model_creator(OrderItemAddon, name="OrderItemAddon")
OrderItemAddonIn_Pydantic = pydantic_model_creator(OrderItemAddon, name="OrderItemAddonIn", exclude_readonly=True)

