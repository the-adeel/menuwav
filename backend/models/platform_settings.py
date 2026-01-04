from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator

class PlatformSettings(Model):
    id = fields.IntField(pk=True)
    platform_fee_percent = fields.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    @classmethod
    async def get_or_create_settings(cls):
        """Get or create the singleton platform settings record (always id=1)"""
        settings = await cls.get_or_none(id=1)
        if not settings:
            settings = await cls.create(id=1, platform_fee_percent=0.00)
        return settings

PlatformSettings_Pydantic = pydantic_model_creator(PlatformSettings, name="PlatformSettings")
PlatformSettingsIn_Pydantic = pydantic_model_creator(PlatformSettings, name="PlatformSettingsIn", exclude_readonly=True)

