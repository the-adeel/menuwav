from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator

class Menu(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    restaurant = fields.ForeignKeyField("models.Restaurant", related_name="menus")

Menu_Pydantic = pydantic_model_creator(Menu, name="Menu")
MenuIn_Pydantic = pydantic_model_creator(Menu, name="MenuIn", exclude_readonly=True)