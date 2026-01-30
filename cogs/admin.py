from disnake.ext import commands
import disnake
from typing import TYPE_CHECKING, cast
import asyncio

if TYPE_CHECKING:
    from cogs import LinkingCog
from modules import autocomplete, mojang
import constants


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
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
    async def admin(self, _: disnake.AppCmdInter):
        return

    @admin.sub_command(
        name="verify",
        description="Verify a Minecraft account with a Discord account",
    )
    async def verify(
        self,
        inter: disnake.AppCmdInter,
        ign: str = commands.Param(
            name="ign",
            description="The Minecraft username or UUID to link the member to.",
            min_length=1,
            max_length=32,
            autocomplete=autocomplete.ign,
        ),
        member: disnake.Member = commands.Param(
            name="member",
            description="The member to verify the Minecraft account to",
        ),
    ):
        await inter.response.defer()
        await self.LinkingCog.hypixel_verify(inter, ign, member)

    @admin.sub_command_group(
        name="force", description="Force admin verification actions"
    )
    async def force(self, _: disnake.AppCmdInter):
        return

    @force.sub_command(
        name="verify",
        description="Forcefully verify a Minecraft account to a user without checking if they own the account. **USE VERY RARELY**",
    )
    async def bypass_verification(
        self,
        inter: disnake.AppCmdInter,
        member: disnake.Member = commands.Param(
            name="member",
            description="The member to bypass the verification process for",
        ),
        ign: str = commands.Param(
            name="ign",
            description="The Minecraft username or UUID to link the member to.",
            min_length=1,
            max_length=32,
            autocomplete=autocomplete.ign,
        ),
        reason: str = commands.param(
            name="reason",
            description="A detailed and valid reason for bypassing the verification process.",
        ),
    ):
        player, _ = await asyncio.gather(
            mojang.get_player(ign),
            inter.response.defer(),
        )
