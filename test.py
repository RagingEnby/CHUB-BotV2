from typing import TYPE_CHECKING
import disnake

if TYPE_CHECKING:
    from main import bot
    from cogs import LinkingCog as LinkingCogType

inter: disnake.AppCmdInter


async def main():
    import datetime
    import json
    import aiofiles
    from typing import cast
    from cogs.linking import LinkedUserDoc

    LinkingCog: LinkingCogType = cast("LinkingCogType", bot.get_cog("LinkingCog"))

    async with aiofiles.open("debug/linkedusers.json", "r") as file:
        # dict[uuid, discord_id]
        data: dict[str, str] = json.loads(await file.read())  # type: ignore
    docs: list[LinkedUserDoc] = [
        {
            "_id": int(discord_id),
            "uuid": uuid,
            "date": datetime.datetime.fromtimestamp(0),
            "source": "hypixel",
            "manualReason": None,
        }
        for uuid, discord_id in data.items()
    ]
    before = datetime.datetime.now()
    await LinkingCog.linked_users_db.insert(*docs)  # type: ignore
    after = datetime.datetime.now()
    await inter.send(f"Inserted {len(docs)} docs in {after - before} seconds")  # type: ignore
