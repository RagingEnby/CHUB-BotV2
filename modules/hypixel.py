from typing import Any
import datetime

from modules import asyncreqs, mojang
import constants


class APIError(Exception):
    def __init__(self, cause: str, status_code: int, msg: str | None = None):
        self.cause = cause
        self.status_code = status_code
        msg = msg or f"Hypixel API error: '{cause}' (status code: {status_code})"
        super().__init__(msg)


class RateLimitError(APIError):
    def __init__(
        self,
        cause: str,
        status_code: int,
        retry_after: int,
        msg: str | None = None,
    ):
        self.cause = cause
        self.status_code = status_code
        self.retry = datetime.timedelta(seconds=retry_after)
        msg = (
            msg
            or f"Hypixel rate limit error: '{cause}' (status_code={status_code}, retry_after={self.retry.total_seconds()})"
        )
        super().__init__(cause=cause, status_code=status_code, msg=msg)


class PlayerRateLimitError(RateLimitError):
    cause_message: str = (
        "You have already looked up this player too recently, please try again shortly"
    )

    def __init__(
        self,
        cause: str,
        status_code: int,
        retry_after: int,
        player: str | None,
    ):
        self.cause = cause
        self.status_code = status_code
        self.retry = datetime.timedelta(seconds=retry_after)
        self.player = player
        super().__init__(
            cause=cause,
            status_code=status_code,
            retry_after=retry_after,
            msg=f"Player rate limit error {'for ' + player + ' ' if player else ''} (status_code={status_code}, retry_after={self.retry.total_seconds()})",
        )


async def get(endpoint: str, **params: Any) -> dict[str, Any]:
    # formulate request
    url = "https://api.hypixel.net/v2" + endpoint
    ign = params.pop("ign", None)
    if ign and isinstance(ign, str):
        player = await mojang.get_player(ign)
        params["uuid"] = player.uuid
    params["key"] = constants.HYPIXEL_API_KEY

    # get data
    response = await asyncreqs.get(url, params=params)
    data = response.json()

    # handle errors
    error = data.get("cause")
    if data.get("cause") == PlayerRateLimitError.cause_message:
        raise PlayerRateLimitError(
            cause=error,
            status_code=response.status_code,
            retry_after=response.headers.get("Retry-After"),
            player=params.get("uuid"),
        )
    if response.status_code == 429:
        raise RateLimitError(
            cause=data["cause"],
            status_code=response.status_code,
            retry_after=response.headers.get("Retry-After"),
        )
    if error:
        raise APIError(cause=data["cause"], status_code=response.status_code)

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
        discord = self.socials.get("DISCORD")
        return discord.lower() if discord else None


async def get_player(identifier: str) -> PlayerData:
    data = await get("/player", ign=identifier)
    return PlayerData(data)
