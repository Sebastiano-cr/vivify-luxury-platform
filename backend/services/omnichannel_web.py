"""Web channel adapter — products already live on marketplace, just tracks sync status."""
from .omnichannel import ChannelAdapter


class WebAdapter(ChannelAdapter):
    async def push_product(self, product: dict, config: dict) -> dict:
        return {
            "success": True,
            "status": "synced",
            "external_id": product.get("id", ""),
            "message": "Product already on marketplace (web channel)",
        }

    async def delete_product(self, external_id: str, config: dict) -> dict:
        return {"success": True, "status": "deleted", "message": "Web channel: product removed from catalog"}

    async def health_check(self, config: dict) -> bool:
        return True
