from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator
import json

class GeneratedMenu(Model):
    id = fields.IntField(pk=True)
    restaurant = fields.ForeignKeyField("models.Restaurant", related_name="generated_menus")
    name = fields.CharField(max_length=255)
    orientation = fields.CharField(max_length=20)  # 'portrait' or 'wide'
    image_path = fields.CharField(max_length=500)
    menu_item_ids = fields.JSONField(default=list)  # List of menu item IDs used
    template_settings = fields.JSONField(default=dict)  # Template, theme, font settings
    created_at = fields.DatetimeField(auto_now_add=True)

GeneratedMenu_Pydantic = pydantic_model_creator(GeneratedMenu, name="GeneratedMenu")
GeneratedMenuIn_Pydantic = pydantic_model_creator(GeneratedMenu, name="GeneratedMenuIn", exclude_readonly=True)

