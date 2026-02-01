import asyncio
from disnake.ext import commands
import disnake
from typing import TYPE_CHECKING, cast, TypedDict
import datetime
import enum

if TYPE_CHECKING:
    from cogs import UtilsCog, LinkingCog
from modules import mongodb, mojang
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


class PunishmentType(enum.Enum):
    BAN = "ban"
    UNBAN = "unban"
    MUTE = "mute"
    UNMUTE = "unmute"


MESSAGE_CLEAN_TIMES: list[disnake.OptionChoice] = [
    disnake.OptionChoice(name="Don't Delete Any", value=0),
    disnake.OptionChoice(name="Previous Hour", value=60 * 60),
    disnake.OptionChoice(name="Previous 6 Hours", value=60 * 60 * 6),
    disnake.OptionChoice(name="Previous 12 Hours", value=60 * 60 * 12),
    disnake.OptionChoice(name="Previous 24 Hours", value=60 * 60 * 24),
    disnake.OptionChoice(name="Previous 3 Days", value=60 * 60 * 24 * 3),
    disnake.OptionChoice(name="Previous 7 Days", value=60 * 60 * 24 * 7),
]

MUTE_DURATIONS: list[disnake.OptionChoice] = [
    disnake.OptionChoice(name="60 Secs", value=60),
    disnake.OptionChoice(name="5 Mins", value=60 * 5),
    disnake.OptionChoice(name="10 Mins", value=60 * 10),
    disnake.OptionChoice(name="1 Hour", value=60 * 60),
    disnake.OptionChoice(name="2 Hours", value=60 * 60 * 2),
    disnake.OptionChoice(name="3 Hours", value=60 * 60 * 3),
    disnake.OptionChoice(name="1 Day", value=60 * 60 * 24),
    disnake.OptionChoice(name="2 Days", value=60 * 60 * 24 * 2),
    disnake.OptionChoice(name="3 Days", value=60 * 60 * 24 * 3),
    disnake.OptionChoice(name="1 Week", value=60 * 60 * 24 * 7),
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

    def format_audit_reason(
        self, user: disnake.User | disnake.Member, reason: str
    ) -> str:
        return f"[@{user.name} - {user.id}] {reason}"

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
            reason=self.format_audit_reason(inter.author, reason),
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
        try:
            await self.UtilsCog.chub.unban(
                user, reason=self.format_audit_reason(inter.author, reason)
            )
        except disnake.NotFound as e:
            return await inter.response.send_message(
                embed=self.UtilsCog.make_error(
                    title="Ban Not Found",
                    description=f"Unable to find the user's ban (`{e}`)",
                )
            )
        await asyncio.gather(
            inter.response.defer(),
            self.on_unban(
                target=user.id,
                user=inter.author.id,
                reason=reason,
            ),
        )
        await inter.send(
            embed=self.UtilsCog.make_success(
                title="Unbanned",
                description="The user has been unbanned from Collector's Hub",
            )
        )

    @moderation.sub_command(name="mute", description="Mute a member")
    async def mute_command(
        self,
        inter: disnake.AppCmdInter,
        member: disnake.Member = commands.Param(description="The user to mute"),
        duration: int = commands.Param(
            description="The duration to mute the user for",
            choices=MUTE_DURATIONS,
        ),
        reason: str = commands.Param(
            description="The reason for the mute. Please write a concise, well though out reason"
        ),
    ):
        await asyncio.gather(
            inter.response.defer(),
            member.timeout(
                duration=duration,
                reason=self.format_audit_reason(inter.author, reason),
            ),
        )
        unmute_at = (
            member.current_timeout
            or datetime.datetime.now() + datetime.timedelta(seconds=duration)
        )
        await asyncio.gather(
            inter.send(
                embed=self.UtilsCog.make_success(
                    title="Muted",
                    description=f"The user has been muted from Collector's Hub, they will be unmuted {disnake.utils.format_dt(unmute_at, 'R')}",
                )
            ),
            self.log_mod_action(
                action=PunishmentType.MUTE,
                user=inter.author.id,
                target=member.id,
                reason=reason,
            ),
        )

    @commands.slash_command(name="unmute", description="Unmute a member")
    async def unmute_command(
        self,
        inter: disnake.AppCmdInter,
        member: disnake.Member = commands.Param(description="The user to unmute"),
        reason: str = commands.Param(
            description="The reason for the unmute. Please write a concise, well though out reason"
        ),
    ):
        if not member.current_timeout:
            return await inter.response.send_message(
                embed=self.UtilsCog.make_error(
                    title="Not Muted",
                    description="The user is not currently muted",
                )
            )
        await asyncio.gather(
            inter.response.defer(),
            member.timeout(
                duration=None, reason=self.format_audit_reason(inter.author, reason)
            ),
        )
        await asyncio.gather(
            inter.send(
                embed=self.UtilsCog.make_success(
                    title="Unmuted",
                    description="The user has been unmuted from Collector's Hub",
                )
            ),
            self.log_mod_action(
                action=PunishmentType.UNMUTE,
                user=inter.author.id,
                target=member.id,
                reason=reason,
            ),
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

    def verbify_punishment(self, action: PunishmentType) -> str:
        if action in {PunishmentType.BAN, PunishmentType.UNBAN}:
            return f"{action.value}ed".title()
        return f"{action.value}d".title()

    async def log_mod_action(
        self,
        action: PunishmentType,
        user: disnake.User | disnake.Member | int | None,
        target: disnake.User | disnake.Member | int,
        target_player: mojang.Player | str | None = None,
        reason: str | None = None,
        date: datetime.datetime | None = None,
    ):
        if isinstance(user, int):
            user = self.UtilsCog.chub.get_member(user) or await self.bot.fetch_user(
                user
            )
        if isinstance(target, int):
            target = self.UtilsCog.chub.get_member(target) or await self.bot.fetch_user(
                target
            )
        if target_player is None:
            doc = await self.LinkingCog.search_verification(discord_id=target.id)
            target_player = doc["uuid"] if doc else None
        if isinstance(target_player, str):
            target_player = await mojang.get_player(target_player)

        description: list[str] = []
        if (
            isinstance(target, disnake.Member)
            and target.current_timeout
            and PunishmentType.MUTE == action
        ):
            description.append(
                f"Mute expires {disnake.utils.format_dt(target.current_timeout, 'R')}\n"
            )
        description.append(
            f"__Discord:__ {target.mention} ([{target.id}]({constants.DISCORD_USER_URL.format(target.id)}))"
        )
        description.append(
            f"__Minecraft:__ `{target_player.name}` ([{target_player.uuid}]({target_player.namemc}))"
            if target_player
            else ""
        )
        embed = disnake.Embed(
            title=f"{target} was {self.verbify_punishment(action)}!",
            color=(
                disnake.Color.green()
                if action in {PunishmentType.UNBAN, PunishmentType.UNMUTE}
                else disnake.Color.red()
            ),
            timestamp=date or datetime.datetime.now(),
            description="\n".join(description),
        )
        embed.set_thumbnail(
            target_player.skin
            if target_player
            else (user.display_avatar.url if user else None)
        )
        if user:
            embed.set_footer(
                text=f"Moderator: {user.display_name} ({user.id})",
                icon_url=user.display_avatar.url,
            )
        else:
            embed.set_footer(text="Moderator: Unknown")
        embed.add_field(name="Reason", value=f"```\n{reason}\n```", inline=False)
        await self.UtilsCog.send_message(
            channel_id=constants.PUNISHMENT_LOG_CHANNEL_ID,
            embed=embed,
        )

    async def on_ban(
        self,
        target: int,
        user: int | None = None,
        reason: str | None = None,
        audit_entry: disnake.AuditLogEntry | None = None,
    ):
        audit_entry = audit_entry or await self.find_audit_entry(
            target, BanUpdateType.BAN
        )
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
        uuid = linked_doc["uuid"] if linked_doc else None
        date = audit_entry.created_at or datetime.datetime.now()
        tasks = [
            self.ban_db.insert(
                {
                    "_id": audit_entry.id,
                    "discordId": target,
                    "uuid": uuid,
                    "date": date,
                    "bannedBy": (
                        user or (audit_entry.user.id if audit_entry.user else None)
                    ),
                    "reason": reason or (audit_entry.reason if audit_entry else None),
                    "unban": None,
                }
            ),
            self.log_mod_action(
                action=PunishmentType.BAN,
                user=user,
                target=target,
                reason=reason,
                date=date,
            ),
        ]
        if reason is None or not reason.strip():
            tasks.append(
                self.UtilsCog.send_message(
                    channel_id=constants.STAFF_CHANNEL_ID,
                    content=f"<@{user}> You banned user <@{target}> without a ban reason. PLEASE remember to always provide a ban reason.",
                )
            )
        await asyncio.gather(*tasks)

    async def on_unban(
        self,
        target: int,
        user: int | None = None,
        reason: str | None = None,
        audit_entry: disnake.AuditLogEntry | None = None,
    ):
        print(f"on_unban(target={target}, user={user}, reason={reason})")
        audit_entry = audit_entry or await self.find_audit_entry(
            target, BanUpdateType.UNBAN
        )
        # avoid duplicate calling of on_unban
        if (
            not user
            and audit_entry
            and audit_entry.user
            and audit_entry.user.id == self.bot.user.id
        ):
            return

        ban = await self.search_ban(discord_id=target)
        if ban is None:
            raise Exception(f"Could not find mongo ban entry for {target}")

        await self.ban_db.update(
            {
                "unban": {
                    "id": audit_entry.id if audit_entry else None,
                    "unbannedBy": (
                        user
                        or (
                            audit_entry.user.id
                            if audit_entry and audit_entry.user
                            else None
                        )
                    ),
                    "reason": reason or (audit_entry.reason if audit_entry else None),
                    "date": audit_entry.created_at
                    if audit_entry
                    else datetime.datetime.now(),
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
        await asyncio.gather(
            self.UtilsCog.safe_dm(
                target, content=constants.CHUB_INVITE_URL, embed=embed
            ),
            self.log_mod_action(
                action=PunishmentType.UNBAN,
                user=user,
                target=target,
                target_player=ban["uuid"],
                reason=reason,
            ),
        )

    @commands.Cog.listener()
    async def on_audit_log_entry_create(self, entry: disnake.AuditLogEntry):
        if (entry.user and entry.user.id == self.bot.user.id) or not entry.target:
            return
        if entry.action == disnake.AuditLogAction.ban:
            await self.on_ban(target=int(entry.target.id), audit_entry=entry)
        elif entry.action == disnake.AuditLogAction.unban:
            await self.on_unban(target=int(entry.target.id), audit_entry=entry)
        elif entry.action == disnake.AuditLogAction.member_update and (
            entry.changes.before.timeout or entry.changes.after.timeout
        ):
            before = entry.changes.before.timeout
            after = entry.changes.after.timeout
            action = PunishmentType.MUTE if after else PunishmentType.UNMUTE
            print(
                f"Member {entry.target.id} {self.verbify_punishment(action)} (before={before}, after={after})"
            )
            await self.log_mod_action(
                action=action,
                user=entry.user.id if entry.user else None,
                target=int(entry.target.id),
                target_player=None,
                reason=entry.reason,
                date=entry.created_at,
            )

    async def close(self):
        await self.ban_db.close()
