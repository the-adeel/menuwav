from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator

class Ingredient(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    restaurant = fields.ForeignKeyField("models.Restaurant", related_name="ingredients")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        unique_together = ("name", "restaurant")

Ingredient_Pydantic = pydantic_model_creator(Ingredient, name="Ingredient")
IngredientIn_Pydantic = pydantic_model_creator(Ingredient, name="IngredientIn", exclude_readonly=True)

