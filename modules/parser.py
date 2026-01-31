import io
import json
from base64 import b64decode
from contextlib import suppress
from typing import Any, TypeAlias

from nbt import nbt


NbtInput: TypeAlias = nbt.NBTFile | nbt.TAG_Compound | nbt.TAG_List | nbt.TAG
JsonObject: TypeAlias = dict[str, Any]


def nbt_to_dict(nbt_data: NbtInput) -> Any:
    if isinstance(nbt_data, (nbt.NBTFile, nbt.TAG_Compound)):
        return {tag.name: nbt_to_dict(tag) for tag in nbt_data.tags}
    elif isinstance(nbt_data, nbt.TAG_List):
        return [nbt_to_dict(item) for item in nbt_data.tags]
    return nbt_data.value


def raw_decode(data: bytes) -> list[JsonObject]:
    with io.BytesIO(data) as fileobj:
        parsed_data = nbt_to_dict(nbt.NBTFile(fileobj=fileobj))
        if (
            isinstance(parsed_data, dict)
            and len(parsed_data) == 1
            and "i" in parsed_data
            and isinstance(parsed_data["i"], list)
        ):
            return parsed_data["i"]
        raise ValueError("Invalid item data", data)


def ensure_all_decoded(value: Any) -> Any:
    if isinstance(value, dict):
        for k, v in value.items():
            if k == "petInfo" and isinstance(v, str):
                with suppress(json.JSONDecodeError):
                    v = json.loads(v)
            value[k] = ensure_all_decoded(v)
        return value
    if isinstance(value, list):
        for idx, item in enumerate(value):
            if isinstance(item, (dict, list)):
                value[idx] = ensure_all_decoded(item)
        return value
    if isinstance(value, bytearray):
        return str(value)
    return value


def decode(item_bytes: str) -> list[JsonObject]:
    decoded = (ensure_all_decoded(i) for i in raw_decode(b64decode(item_bytes)))
    return [i for i in decoded if i]


def decode_single(item_bytes: str) -> JsonObject:
    return decode(item_bytes)[0]
