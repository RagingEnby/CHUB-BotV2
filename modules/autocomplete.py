import disnake
import asyncio

from modules import ragingenbyapi
import constants


def log_autocomplete(inter: disnake.AppCmdInter, user_input: str, field: str):
    print(f"[Autocomplete - {field} - {inter.author.name}] '{user_input}'")


async def ign(
    inter: disnake.AppCmdInter, user_input: str
) -> list[disnake.OptionChoice]:
    log_autocomplete(inter, user_input, "ign")
    user_input = user_input.lower().strip()
    if not user_input:
        return [
            disnake.OptionChoice(name=ign, value=ign) for ign in constants.ADMIN_IGNS
        ]
    try:
        players = await asyncio.wait_for(
            ragingenbyapi.search_ign_stem(user_input), timeout=5
        )
    except asyncio.TimeoutError:
        return [disnake.OptionChoice(name=user_input, value=user_input)]
    return (
        [
            disnake.OptionChoice(name=player.name, value=player.uuid)
            for player in players
        ]
        + [disnake.OptionChoice(name=user_input, value=user_input)]
    )[:25]
