from modules import asyncreqs, mojang
import constants

stem_cache: dict[str, list[mojang.Player]] = {}


async def search_ign_stem(stem: str) -> list[mojang.Player]:
    stem = stem.lower().strip()
    if not stem:
        return []
    if stem in stem_cache:
        return stem_cache[stem].copy()
    response = await asyncreqs.get(constants.IGN_STEM_URL.format(stem))
    if response.status_code != 200:
        print(f"Failed to search for ign stem {stem}: {response.status_code}")
        return []
    stem_cache[stem] = [mojang.Player.from_dict(player) for player in response.json()]
    return stem_cache[stem]
