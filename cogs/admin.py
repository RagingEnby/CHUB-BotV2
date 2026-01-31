from disnake.ext import commands
import disnake
from typing import TYPE_CHECKING, cast
import asyncio

if TYPE_CHECKING:
    from cogs import LinkingCog, UtilsCog
from modules import autocomplete, mojang
import constants


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @property
    def LinkingCog(self) -> "LinkingCog":
        return cast("LinkingCog", self.bot.get_cog("LinkingCog"))

    @property
    def UtilsCog(self) -> "UtilsCog":
        return cast("UtilsCog", self.bot.get_cog("UtilsCog"))

    async def cog_slash_command_check(self, inter: disnake.AppCmdInter) -> bool:
        return await self.bot.is_owner(inter.author)

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
        await self.LinkingCog.hypixel_verify(inter, ign, member)

    @admin.sub_command(
        name="update",
        description="Update a member's synced roles and display name",
    )
    async def update(
        self,
        inter: disnake.AppCmdInter,
        member: disnake.Member = commands.Param(
            name="member",
            description="The member to update",
        ),
    ):
        await self.LinkingCog.update_member(member=member)
        return await inter.send(
            embed=self.UtilsCog.make_success(
                title="Updated",
                description="The member's synced roles and display name have been updated.",
            )
        )

    @admin.sub_command_group(
        name="force", description="Force admin verification actions"
    )
    async def force(self, _: disnake.AppCmdInter):
        return

    @force.sub_command(
        name="verify",
        description="Forcefully verify a Minecraft account to a user. **USE VERY RARELY**",
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
        await self.LinkingCog.log_verification(
            discord_id=member.id,
            uuid=player.uuid,
            source="manual",
            manual_reason=f"[{inter.author.id}] {reason}",
        )
        await inter.send(
            embed=self.UtilsCog.make_success(
                title="Verified",
                description="The Minecraft account has been linked to the Discord account.",
            )
        )
