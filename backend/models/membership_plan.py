from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator
from decimal import Decimal

class MembershipPlan(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    price = fields.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    stripe_price_id = fields.CharField(max_length=255, null=True)  # Stripe Price ID (required for all plans)
    billing_interval = fields.CharField(max_length=10, default="month")  # "day" or "month"
    features = fields.JSONField(default=dict)  # Store feature limits/benefits as JSON
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

MembershipPlan_Pydantic = pydantic_model_creator(MembershipPlan, name="MembershipPlan")
MembershipPlanIn_Pydantic = pydantic_model_creator(MembershipPlan, name="MembershipPlanIn", exclude_readonly=True)

