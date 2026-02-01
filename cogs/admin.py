from disnake.ext import commands
import disnake
from typing import TYPE_CHECKING, cast
import asyncio

if TYPE_CHECKING:
    from cogs import LinkingCog, UtilsCog, ModerationCog
from cogs.moderation import ModAction
from modules import autocomplete, mojang


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @property
    def LinkingCog(self) -> "LinkingCog":
        return cast("LinkingCog", self.bot.get_cog("LinkingCog"))

    @property
    def UtilsCog(self) -> "UtilsCog":
        return cast("UtilsCog", self.bot.get_cog("UtilsCog"))

    @property
    def ModerationCog(self) -> "ModerationCog":
        return cast("ModerationCog", self.bot.get_cog("ModerationCog"))

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
    async def verify_command(
        self,
        inter: disnake.AppCmdInter,
        ign: str = commands.Param(
            description="The Minecraft username or UUID to link the member to.",
            min_length=1,
            max_length=32,
            autocomplete=autocomplete.ign,
        ),
        member: disnake.Member = commands.Param(
            description="The member to verify the Minecraft account to",
        ),
    ):
        await self.LinkingCog.do_verify_command(inter, ign, member)

    @admin.sub_command(
        name="unverify",
        description="Unverify a Minecraft account from a Discord account",
    )
    async def unverify_command(
        self,
        inter: disnake.AppCmdInter,
        member: disnake.Member = commands.Param(
            description="The member to unverify the Minecraft account from",
        ),
    ):
        await self.LinkingCog.do_unverify_command(inter, member)

    @admin.sub_command(
        name="update",
        description="Update a member's synced roles and display name",
    )
    async def update_command(
        self,
        inter: disnake.AppCmdInter,
        member: disnake.Member = commands.Param(
            name="member",
            description="The member to update",
        ),
    ):
        await self.LinkingCog.do_update_command(inter=inter, member=member)

    # the only way to add spaces in slash command names is to use a sub group. the only way to add spaces in
    # sub command names is to use a sub GROUP. so we make a group "force" just so we can make the command name
    # be "/admin force verify"
    @admin.sub_command_group(
        name="force", description="Force admin verification actions"
    )
    async def force(self, _: disnake.AppCmdInter):
        return

    @force.sub_command(
        name="verify",
        description="Forcefully verify a Minecraft account to a user. **USE VERY RARELY**",
    )
    async def force_verify_command(
        self,
        inter: disnake.AppCmdInter,
        member: disnake.Member = commands.Param(
            description="The member to bypass the verification process for",
        ),
        ign: str = commands.Param(
            description="The Minecraft username or UUID to link the member to.",
            min_length=1,
            max_length=32,
            autocomplete=autocomplete.ign,
        ),
        reason: str = commands.param(
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
        await asyncio.gather(
            self.LinkingCog.update_member(member=member),
            self.ModerationCog.log_mod_action(
                action=ModAction.BYPASS_VERIFICATION,
                user=inter.author.id,
                target=member.id,
                target_player=player,
                reason=reason,
                date=inter.created_at,
            ),
        )
        await inter.send(
            embed=self.UtilsCog.make_success(
                title="Verified",
                description="The Minecraft account has been linked to the Discord account.",
            )
        )
