from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator

class MenuItem(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    price = fields.DecimalField(max_digits=10, decimal_places=2)
    image_url = fields.CharField(max_length=500, null=True)
    menu = fields.ForeignKeyField("models.Menu", related_name="items")
    external_id = fields.CharField(max_length=255, null=True)  # Custom ID for duplicate prevention

MenuItem_Pydantic = pydantic_model_creator(MenuItem, name="MenuItem")
MenuItemIn_Pydantic = pydantic_model_creator(MenuItem, name="MenuItemIn", exclude_readonly=True)