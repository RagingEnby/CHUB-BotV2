"""BASE COG - NOT FOR USAGE"""

import asyncio
from disnake.ext import commands
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from cogs import UtilsCog


class BaseCog(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot
        self.task: asyncio.Task | None = None

    @property
    def UtilsCog(self) -> "UtilsCog":
        return cast("UtilsCog", self.bot.get_cog("UtilsCog"))

    async def main(self):
        while True:
            print("[BaseCog] main() loop")
            await asyncio.sleep(30)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.close()
        self.task = asyncio.create_task(self.main())

    async def close(self):
        if self.task is not None and not self.task.done():
            self.task.cancel()
            self.task = None
