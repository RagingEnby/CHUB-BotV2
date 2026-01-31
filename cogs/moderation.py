import asyncio
from disnake.ext import commands
import disnake
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from cogs import UtilsCog


class ModerationCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.task: asyncio.Task | None = None

    @property
    def UtilsCog(self) -> "UtilsCog":
        return cast("UtilsCog", self.bot.get_cog("UtilsCog"))

    async def cog_slash_command_check(self, inter: disnake.AppCmdInter) -> bool:
        return self.UtilsCog.is_staff(inter.author)
