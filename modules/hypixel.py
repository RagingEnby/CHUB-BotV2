from typing import Any
from modules import asyncreqs, minecraft
import constants


class HypixelAPIError(Exception):
    def __init__(self, cause: str, status_code: int):
        self.cause = cause
        self.status_code = status_code
        super().__init__(f"Hypixel API error: {cause} (status code: {status_code})")


async def get(endpoint: str, **params: Any) -> dict[str, Any]:
    url = "https://api.hypixel.net/v2" + endpoint
    ign = params.pop("ign", None)
    if ign and isinstance(ign, str):
        player = await minecraft.get_player(ign)
        params["uuid"] = player.uuid
    params["key"] = constants.HYPIXEL_API_KEY
    response = await asyncreqs.get(url, params=params)
    data = response.json()
    if data.get("cause"):
        raise HypixelAPIError(data["cause"], response.status_code)
    return data


class PlayerData:
    def __init__(self, data: dict[str, Any]):
        self.data = data

    @property
    def player(self) -> dict[str, Any]:
        return self.data.get("player") or {}

    @property
    def socials(self) -> dict[str, Any]:
        return self.player.get("socialMedia", {}).get("links", {})

    @property
    def discord(self) -> str | None:
        return self.socials.get("DISCORD")


async def get_player(identifier: str) -> PlayerData:
    data = await get("/player", ign=identifier)
    return PlayerData(data)


async def get_discord(identifier: str) -> str | None:
    data = await get_player(identifier)
    return data.discord
