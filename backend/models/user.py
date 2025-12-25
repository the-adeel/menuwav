# models/user.py
from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator
from enum import Enum

class Role(str, Enum):
    CUSTOMER = "customer"
    RESTAURANT_ADMIN = "restaurant_admin"
    SUPERADMIN = "superadmin"

class User(Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=255, unique=True)
    password = fields.CharField(max_length=255)  # hashed
    role = fields.CharEnumField(Role, default=Role.CUSTOMER)
    email = fields.CharField(max_length=255, null=True)
    phone = fields.CharField(max_length=20, null=True)

User_Pydantic = pydantic_model_creator(User, name="User")
UserIn_Pydantic = pydantic_model_creator(User, name="UserIn", exclude_readonly=True, exclude=("password",))