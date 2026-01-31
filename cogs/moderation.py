import asyncio
from disnake.ext import commands
import disnake
from typing import TYPE_CHECKING, cast, TypedDict
import datetime
import enum

if TYPE_CHECKING:
    from cogs import UtilsCog, LinkingCog
from modules import mongodb
import constants


class UnbanDoc(TypedDict):
    id: int | None
    unbannedBy: int | None
    reason: str | None
    date: datetime.datetime


class BanDoc(TypedDict):
    _id: int
    discordId: int
    uuid: str | None
    date: datetime.datetime
    bannedBy: int | None
    reason: str
    unban: UnbanDoc | None


class BanUpdateType(enum.Enum):
    BAN = "ban"
    UNBAN = "unban"


MESSAGE_CLEAN_TIMES: list[disnake.OptionChoice] = [
    disnake.OptionChoice(name="Don't Delete Any", value=0),
    disnake.OptionChoice(name="Previous Hour", value=60 * 60),
    disnake.OptionChoice(name="Previous 6 Hours", value=60 * 60 * 6),
    disnake.OptionChoice(name="Previous 12 Hours", value=60 * 60 * 12),
    disnake.OptionChoice(name="Previous 24 Hours", value=60 * 60 * 24),
    disnake.OptionChoice(name="Previous 3 Days", value=60 * 60 * 24 * 3),
    disnake.OptionChoice(name="Previous 7 Days", value=60 * 60 * 24 * 7),
]


class ModerationCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.task: asyncio.Task | None = None
        self.ban_db = mongodb.Collection(constants.BAN_COLLECTION_NAME)

    @property
    def UtilsCog(self) -> "UtilsCog":
        return cast("UtilsCog", self.bot.get_cog("UtilsCog"))

    @property
    def LinkingCog(self) -> "LinkingCog":
        return cast("LinkingCog", self.bot.get_cog("LinkingCog"))

    async def cog_slash_command_check(self, inter: disnake.AppCmdInter) -> bool:
        return self.UtilsCog.is_staff(inter.author)

    @commands.slash_command(name="moderation", description="Moderation commands")
    async def moderation(self, _: disnake.AppCmdInter):
        return

    @moderation.sub_command(name="ban", description="Ban a member")
    async def ban_command(
        self,
        inter: disnake.AppCmdInter,
        member: disnake.Member = commands.Param(description="The user to ban"),
        reason: str = commands.Param(
            description="The reason for the ban. Please write a concise, well though out reason"
        ),
        delete_messages: int = commands.Param(
            description="How much of their message history to wipe. Defaults to 0",
            choices=MESSAGE_CLEAN_TIMES,
            default=0,
        ),
    ):
        embed = disnake.Embed(
            title="You have been banned from Collector's Hub",
            description="You have been banned from Collector's Hub. If you have any questions or you would like to appeal your ban, please join the appeals server.",
            color=disnake.Color.red(),
        )
        embed.add_field(
            name="Ban Reason",
            value=f"```\n{reason}\n```",
        )
        embed.set_footer(
            text=f"Banned by {inter.author.name} ({inter.author.id})",
            icon_url=inter.author.display_avatar.url,
        )
        await asyncio.gather(
            inter.response.defer(),
            self.UtilsCog.safe_dm(
                member, content=constants.APPEALS_INVITE_URL, embed=embed
            ),
        )
        await member.ban(
            reason=f"[@{inter.author.name} - {inter.author.id}] {reason}",
            clean_history_duration=delete_messages,
        )
        await self.on_ban(
            target=member.id,
            user=inter.author.id,
            reason=reason,
        )
        await inter.send(
            embed=self.UtilsCog.make_success(
                title="Banned",
                description="The user has been banned from Collector's Hub",
            )
        )

    @moderation.sub_command(name="unban", description="Unban a member")
    async def unban_command(
        self,
        inter: disnake.AppCmdInter,
        user: disnake.User = commands.Param(
            description="The user to unban (usually you'll need to paste a user ID)"
        ),
        reason: str = commands.Param(
            description="The reason for the unban. Please write a concise, well though out reason"
        ),
    ):
        await inter.response.defer()
        try:
            await self.UtilsCog.chub.unban(
                user, reason=f"[@{inter.author.name} - {inter.author.id}] {reason}"
            )
        except disnake.NotFound as e:
            return await inter.send(
                embed=self.UtilsCog.make_error(
                    title="Ban Not Found",
                    description=f"Unable to find the user's ban (`{e}`)",
                )
            )
        await self.on_unban(
            target=user.id,
            user=inter.author.id,
            reason=reason,
        )
        await inter.send(
            embed=self.UtilsCog.make_success(
                title="Unbanned",
                description="The user has been unbanned from Collector's Hub",
            )
        )

    async def search_ban(self, discord_id: int) -> BanDoc | None:
        docs: list[BanDoc] = cast(
            "list[BanDoc]",
            await self.ban_db.get_many(
                {"discordId": discord_id, "unban": None}, sort={"date": -1}
            ),
        )
        return docs[0] if docs else None

    async def find_audit_entry(
        self, target: int, type_: BanUpdateType
    ) -> disnake.AuditLogEntry | None:
        async for entry in self.UtilsCog.chub.audit_logs(
            limit=10,
            action=(
                disnake.AuditLogAction.unban
                if type_ == BanUpdateType.UNBAN
                else disnake.AuditLogAction.ban
            ),
        ):
            if entry.target and entry.target.id == target:
                return entry
        return None

    async def on_ban(
        self,
        target: int,
        user: int | None = None,
        reason: str | None = None,
    ):
        audit_entry = await self.find_audit_entry(target, BanUpdateType.BAN)
        if not audit_entry:
            raise Exception(f"Could not find ban audit log entry for {target}")

        if (
            not user
            and audit_entry
            and audit_entry.user
            and audit_entry.user.id == self.bot.user.id
        ):
            return

        if await self.ban_db.get({"_id": audit_entry.id}, projection={"_id": 1}):
            print(f"Ignoring duplicate ban entry: {audit_entry.id}")
            return

        linked_doc = await self.LinkingCog.search_verification(discord_id=target)
        await self.ban_db.insert(
            {
                "_id": audit_entry.id,
                "discordId": target,
                "uuid": linked_doc["uuid"] if linked_doc else None,
                "date": audit_entry.created_at or datetime.datetime.now(),
                "bannedBy": user or audit_entry.user.id if audit_entry.user else None,
                "reason": reason or audit_entry.reason if audit_entry else None,
                "unban": None,
            }
        )
        if reason is None or not reason.strip():
            await self.UtilsCog.send_message(
                channel_id=constants.STAFF_CHANNEL_ID,
                content=f"<@{user}> You banned user <@{target}> without a ban reason. PLEASE remember to always provide a ban reason.",
            )

    async def on_unban(
        self,
        target: int,
        user: int | None = None,
        reason: str | None = None,
    ):
        print(f"on_unban(target={target}, user={user}, reason={reason})")
        ban, unban = await asyncio.gather(
            self.search_ban(discord_id=target),
            self.find_audit_entry(target, BanUpdateType.UNBAN),
        )
        if ban is None:
            raise Exception(f"Could not find ban entry for {target}")

        # avoid duplicate calling of on_unabn
        if not user and unban and unban.user == self.bot.user.id:
            return
        await self.ban_db.update(
            {
                "unban": {
                    "id": unban.id if unban else None,
                    "unbannedBy": (
                        user or unban.user.id if unban and unban.user else None
                    ),
                    "reason": reason or unban.reason if unban else None,
                    "date": unban.created_at if unban else datetime.datetime.now(),
                }
            },
            query={"_id": ban["_id"]},
        )
        embed = disnake.Embed(
            title="You have been unbanned from Collector's Hub",
            description="You have been unbanned from Collector's Hub. You may now rejoin the server using the attached invite link.",
            color=disnake.Color.green(),
        )
        embed.add_field(
            name="Unban Reason",
            value=f"```\n{reason}\n```",
        )
        user_obj = self.UtilsCog.chub.get_member(user) if user else None
        if user_obj:
            embed.set_footer(
                text=f"Unbanned by {user_obj} ({user_obj.id})",
                icon_url=user_obj.display_avatar.url,
            )
        await self.UtilsCog.safe_dm(
            target, content=constants.CHUB_INVITE_URL, embed=embed
        )

    @commands.Cog.listener()
    async def on_raw_member_remove(self, payload: disnake.RawGuildMemberRemoveEvent):
        if payload.guild_id != constants.GUILD_ID:
            return
        await self.on_ban(payload.user.id)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: disnake.Guild, user: disnake.User):
        if guild.id != constants.GUILD_ID:
            return
        await self.on_unban(user.id)

    async def close(self):
        self.ban_db.close()
