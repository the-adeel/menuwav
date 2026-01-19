from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator

class Addon(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    price_adjustment = fields.DecimalField(max_digits=10, decimal_places=2)
    image_url = fields.CharField(max_length=500, null=True)
    is_available = fields.BooleanField(default=True)
    restaurant = fields.ForeignKeyField("models.Restaurant", related_name="addons")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        unique_together = ("name", "restaurant")

Addon_Pydantic = pydantic_model_creator(Addon, name="Addon")
AddonIn_Pydantic = pydantic_model_creator(Addon, name="AddonIn", exclude_readonly=True)

