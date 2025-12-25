from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator
from enum import Enum

class QRType(str, Enum):
    TABLE = "table"
    RESTAURANT = "restaurant"

class QRCode(Model):
    id = fields.IntField(pk=True)
    restaurant = fields.ForeignKeyField("models.Restaurant", related_name="qr_codes")
    table_number = fields.IntField(null=True)
    qr_type = fields.CharEnumField(QRType)
    qr_data = fields.CharField(max_length=500)  # URL
    created_at = fields.DatetimeField(auto_now_add=True)

QRCode_Pydantic = pydantic_model_creator(QRCode, name="QRCode")
QRCodeIn_Pydantic = pydantic_model_creator(QRCode, name="QRCodeIn", exclude_readonly=True)

