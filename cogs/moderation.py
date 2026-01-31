import asyncio
from disnake.ext import commands
import disnake
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from cogs import UtilsCog
import constants


class ModerationCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.task: asyncio.Task | None = None

    @property
    def UtilsCog(self) -> "UtilsCog":
        return cast("UtilsCog", self.bot.get_cog("UtilsCog"))

    async def cog_slash_command_check(self, inter: disnake.AppCmdInter) -> bool:
        if isinstance(inter.author, disnake.User):
            return await self.bot.is_owner(inter.author)
        return (
            await self.bot.is_owner(inter.author)
            or inter.author.get_role(constants.STAFF_ROLE_ID) is not None
        )
