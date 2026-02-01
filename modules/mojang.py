import re
import asyncio
import json

from modules import asyncreqs
import constants


class Player:
    def __init__(self, uuid: str, name: str):
        self.uuid = uuid.replace("-", "")
        self.name = name

    @property
    def avatar(self) -> str:
        return constants.MC_AVATAR_URL.format(self.uuid)

    @property
    def skin(self) -> str:
        return constants.MC_SKIN_URL.format(self.uuid)

    @property
    def namemc(self) -> str:
        return constants.NAMEMC_URL.format(self.name)

    def __str__(self) -> str:
        return self.name

    @classmethod
    def from_dict(cls, data: dict) -> "Player":
        uuid = data.get("id", data.get("uuid", data.get("playerUuid")))
        name = data.get("name", data.get("username", data.get("playerName")))
        if not uuid or not name:
            raise ValueError(f"Invalid player data: {data}")
        return cls(uuid=uuid, name=name)


class MojangAPIError(Exception):
    def __init__(self, error_message: str, status_code: int):
        self.error_message = error_message
        self.status_code = status_code
        super().__init__(
            f"Mojang API error: {error_message} (status code: {status_code})"
        )


class PlayerNotFound(MojangAPIError):
    def __init__(self, identifier: str):
        self.identifier = identifier
        super().__init__(f"Player not found: {identifier}", 404)


async def get_player(identifier: str, attempts: int = 0) -> Player:
    identifier = identifier.lower().replace("-", "")
    if not is_identifier(identifier):
        raise PlayerNotFound(identifier)

    response = await asyncreqs.get(constants.MOJANG_API_URL.format(identifier))
    if response.status_code == 404:
        raise PlayerNotFound(identifier)
    try:
        data = response.json()
    except json.JSONDecodeError:
        print(
            "invalid mojang response for",
            identifier,
            response.status_code,
            response.text,
        )
        if attempts > 3:
            raise PlayerNotFound(identifier)
        await asyncio.sleep(0.5)
        return await get_player(identifier, attempts + 1)
    error = data.get("errorMessage")
    if error:
        raise MojangAPIError(error, response.status_code)
    return Player.from_dict(data)


async def get_players(*identifiers: str) -> list[Player]:
    identifiers_set = set(identifiers)
    return await asyncio.gather(
        *[get_player(identifier) for identifier in identifiers_set]
    )


def is_uuid(uuid: str) -> bool:
    if not len(uuid) > 16:
        return False
    uuid = uuid.replace("-", "")
    return re.fullmatch(constants.UUID_REGEX, uuid) is not None


def is_username(username: str) -> bool:
    return re.fullmatch(constants.USERNAME_REGEX, username) is not None


def is_identifier(identifier: str) -> bool:
    return is_uuid(identifier) or is_username(identifier)
