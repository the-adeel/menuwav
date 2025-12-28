from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator

class MenuItemAddon(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    price_adjustment = fields.DecimalField(max_digits=10, decimal_places=2)
    image_url = fields.CharField(max_length=500, null=True)
    menu_item = fields.ForeignKeyField("models.MenuItem", related_name="addons")
    is_available = fields.BooleanField(default=True)

MenuItemAddon_Pydantic = pydantic_model_creator(MenuItemAddon, name="MenuItemAddon")
MenuItemAddonIn_Pydantic = pydantic_model_creator(MenuItemAddon, name="MenuItemAddonIn", exclude_readonly=True)

