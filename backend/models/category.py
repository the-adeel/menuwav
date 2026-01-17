from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator

class Category(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    restaurant = fields.ForeignKeyField("models.Restaurant", related_name="categories")

Category_Pydantic = pydantic_model_creator(Category, name="Category")
CategoryIn_Pydantic = pydantic_model_creator(Category, name="CategoryIn", exclude_readonly=True)

