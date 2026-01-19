from tortoise.models import Model
from tortoise import fields

class MenuItemAddon(Model):
    id = fields.IntField(pk=True)
    menu_item = fields.ForeignKeyField("models.MenuItem", related_name="menu_item_addons")
    addon = fields.ForeignKeyField("models.Addon", related_name="menu_item_addons")

    class Meta:
        unique_together = ("menu_item", "addon")
