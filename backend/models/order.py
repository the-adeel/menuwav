from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator
from enum import Enum

class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY = "ready"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class Order(Model):
    id = fields.IntField(pk=True)
    restaurant = fields.ForeignKeyField("models.Restaurant", related_name="orders")
    customer = fields.ForeignKeyField("models.User", related_name="orders", null=True)
    table_number = fields.IntField(null=True)
    status = fields.CharEnumField(OrderStatus, default=OrderStatus.PENDING)
    total = fields.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = fields.DatetimeField(auto_now_add=True)

Order_Pydantic = pydantic_model_creator(Order, name="Order")
OrderIn_Pydantic = pydantic_model_creator(Order, name="OrderIn", exclude_readonly=True)

