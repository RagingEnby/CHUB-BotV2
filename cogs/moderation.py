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
    unbannedBy: int
    reason: str
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
        await asyncio.gather(
            inter.response.defer(),
            member.ban(
                reason=f"[@{inter.author.name} - {inter.author.id}] {reason}",
                clean_history_duration=delete_messages,
            ),
        )
        ban_entry = await self.find_audit_entry(member.id, BanUpdateType.BAN)
        if ban_entry is None:
            return await inter.send(
                embed=self.UtilsCog.make_error(
                    title="Unable To Find Ban Entry",
                    description="The user was successfully banned, but I was unable to find the ban entry in order to log it to the ban database. This is a major error, **PLEASE CONTACT RAGINGENBY**",
                )
            )
        await self.on_ban(
            ban_id=ban_entry.id,
            target=member.id,
            user=inter.author.id,
            date=ban_entry.created_at,
            reason=reason,
        )
        await inter.send(
            embed=self.UtilsCog.make_success(
                title="Banned", description="The user has been banned from the server"
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
        ban_id: int,
        target: int,
        user: int | None,
        date: datetime.datetime,
        reason: str | None = None,
    ):
        if await self.ban_db.get({"_id": ban_id}, projection={"_id": 1}):
            print(f"Ignoring duplicate ban entry: {ban_id}")
            return
        linked_doc = await self.LinkingCog.search_verification(discord_id=target)
        await self.ban_db.insert(
            {
                "_id": ban_id,
                "discordId": target,
                "uuid": linked_doc["uuid"] if linked_doc else None,
                "date": date,
                "bannedBy": user,
                "reason": reason,
                "unban": None,
            }
        )
        if not reason:
            await self.UtilsCog.send_message(
                channel_id=constants.STAFF_CHANNEL_ID,
                content=f"<@{user}> You banned user <@{target}> without a ban reason. PLEASE remember to always provide a ban reason.",
            )

    @commands.Cog.listener()
    async def on_raw_member_remove(self, payload: disnake.RawGuildMemberRemoveEvent):
        ban_entry = await self.find_audit_entry(payload.user.id, BanUpdateType.BAN)
        if ban_entry is None:
            return
        banner = ban_entry.user.id if ban_entry.user else None
        if banner == self.bot.user.id:
            return
        await self.on_ban(
            ban_id=ban_entry.id,
            target=payload.user.id,
            user=banner,
            date=ban_entry.created_at,
            reason=ban_entry.reason,
        )

    @commands.Cog.listener()
    async def on_member_unban(self, guild: disnake.Guild, user: disnake.User):
        return

    async def close(self):
        self.ban_db.close()
