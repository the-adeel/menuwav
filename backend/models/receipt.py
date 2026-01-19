from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator

class Receipt(Model):
    id = fields.IntField(pk=True)
    restaurant = fields.ForeignKeyField("models.Restaurant", related_name="receipts")
    order = fields.ForeignKeyField("models.Order", related_name="receipts")
    printed_at = fields.DatetimeField(auto_now_add=True)
    printer_name = fields.CharField(max_length=255)
    receipt_data = fields.TextField()  # Formatted receipt content
    printed_by = fields.ForeignKeyField("models.User", related_name="printed_receipts")

Receipt_Pydantic = pydantic_model_creator(Receipt, name="Receipt")
ReceiptIn_Pydantic = pydantic_model_creator(Receipt, name="ReceiptIn", exclude_readonly=True)

