from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator
from enum import Enum

class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    EXPIRED = "expired"
    TRIALING = "trialing"

class RestaurantSubscription(Model):
    id = fields.IntField(pk=True)
    restaurant = fields.ForeignKeyField("models.Restaurant", related_name="subscription", unique=True)  # One-to-one relationship
    plan = fields.ForeignKeyField("models.MembershipPlan", related_name="subscriptions")
    stripe_subscription_id = fields.CharField(max_length=255, unique=True)  # Required for all plans, including free
    status = fields.CharEnumField(SubscriptionStatus, default=SubscriptionStatus.ACTIVE)
    current_period_start = fields.DatetimeField()
    current_period_end = fields.DatetimeField()
    cancel_at_period_end = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

RestaurantSubscription_Pydantic = pydantic_model_creator(RestaurantSubscription, name="RestaurantSubscription")
RestaurantSubscriptionIn_Pydantic = pydantic_model_creator(RestaurantSubscription, name="RestaurantSubscriptionIn", exclude_readonly=True)

