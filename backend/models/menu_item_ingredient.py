from tortoise.models import Model
from tortoise import fields

class MenuItemIngredient(Model):
    id = fields.IntField(pk=True)
    menu_item = fields.ForeignKeyField("models.MenuItem", related_name="menu_item_ingredients")
    ingredient = fields.ForeignKeyField("models.Ingredient", related_name="menu_item_ingredients")

    class Meta:
        unique_together = ("menu_item", "ingredient")

