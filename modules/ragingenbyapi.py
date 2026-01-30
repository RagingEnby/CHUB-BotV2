from modules import asyncreqs, mojang
import constants


async def search_ign_stem(stem: str) -> list[mojang.Player]:
    stem = stem.lower().strip()
    if not stem:
        return []
    response = await asyncreqs.get(constants.IGN_STEM_URL.format(stem))
    if response.status_code != 200:
        print(f"Failed to search for ign stem {stem}: {response.status_code}")
        return []
    data = response.json()
    return [mojang.Player.from_dict(player) for player in data]
