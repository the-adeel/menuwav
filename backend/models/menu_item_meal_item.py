from tortoise.models import Model
from tortoise import fields

class MenuItemMealItem(Model):
    id = fields.IntField(pk=True)
    menu_item = fields.ForeignKeyField("models.MenuItem", related_name="menu_item_meal_items")
    meal_item = fields.ForeignKeyField("models.MealItem", related_name="menu_item_meal_items")

    class Meta:
        unique_together = ("menu_item", "meal_item")

