from disnake.ext import commands
import disnake
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from cogs import LinkingCog


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    @property
    def LinkingCog(self) -> "LinkingCog":
        return cast("LinkingCog", self.bot.get_cog("LinkingCog"))

    async def cog_slash_command_check(self, inter: disnake.AppCmdInter) -> bool:
        return await self.bot.is_owner(inter.author)

    @commands.slash_command(
        name="admin", description="Admin-only commands for bot development/moderation"
    )
    async def admin(self, inter: disnake.AppCmdInter):
        await inter.response.defer()

    @admin.sub_command(
        name="verify",
        description="Verify a Minecraft account with a Discord account",
    )
    async def verify(
        self, inter: disnake.AppCmdInter, ign: str, member: disnake.Member
    ):
        await self.LinkingCog.verify(inter, ign, member)
