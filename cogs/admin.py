from disnake.ext import commands
import disnake
from typing import TYPE_CHECKING, cast

from modules import autocomplete
import constants

if TYPE_CHECKING:
    from cogs import LinkingCog


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    @property
    def LinkingCog(self) -> "LinkingCog":
        return cast("LinkingCog", self.bot.get_cog("LinkingCog"))

    async def cog_slash_command_check(self, inter: disnake.AppCmdInter) -> bool:
        if isinstance(inter.author, disnake.User):
            return await self.bot.is_owner(inter.author)
        return (
            await self.bot.is_owner(inter.author)
            or inter.author.get_role(constants.STAFF_ROLE_ID) is not None
        )

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
        self,
        inter: disnake.AppCmdInter,
        ign: str = commands.Param(
            name="ign",
            description="The Minecraft username to verify to the selected member",
            default=None,
            min_length=1,
            max_length=16,
            autocomplete=autocomplete.ign,
        ),
        member: disnake.Member = commands.Param(
            name="member",
            description="The member to verify the Minecraft account to",
            default=None,
        ),
    ):
        await self.LinkingCog.verify(inter, ign, member)
