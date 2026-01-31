import asyncio
import datetime
from typing import Literal, TypedDict
from disnake.ext import commands
import disnake
from typing import TYPE_CHECKING, Any, cast

from pymongo.results import DeleteResult

if TYPE_CHECKING:
    from cogs import UtilsCog
from modules import hypixel, autocomplete, mongodb, mojang
import constants

LinkSource = Literal["hypixel", "manual"]


class LinkedUserDoc(TypedDict):
    _id: int
    uuid: str
    date: datetime.datetime
    source: LinkSource
    manualReason: str | None


class LinkingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.task: asyncio.Task | None = None
        self.linked_users_db = mongodb.Collection(constants.LINKED_COLLECTION_NAME)

    @property
    def UtilsCog(self) -> "UtilsCog":
        return cast("UtilsCog", self.bot.get_cog("UtilsCog"))

    class MismatchedDiscordError(Exception):
        def __init__(self, expected: str, real: str | None, identifier: str):
            self.expected = expected
            self.real = real
            self.identifier = identifier
            super().__init__(
                f"Expected Discord username {expected} but got {real} for {identifier}"
            )

    class DiscordAlreadyVerifiedError(Exception):
        def __init__(
            self,
            discord_id: int,
            verified_to: mojang.Player,
            attempt_verified_to: mojang.Player,
        ):
            self.discord_id = discord_id
            self.verified_to = verified_to
            self.attempt_verified_to = attempt_verified_to
            super().__init__(
                f"User {discord_id} is already verified to {verified_to}. Attempted to verify to {attempt_verified_to}."
            )

    class MinecraftAlreadyVerifiedError(Exception):
        def __init__(
            self, player: mojang.Player, verified_to: int, attempt_verified_to: int
        ):
            self.player = player
            self.verified_to = verified_to
            self.attempt_verified_to = attempt_verified_to
            super().__init__(
                f"Player {player.name} is already verified to {verified_to}. Attempted to verify to {attempt_verified_to}."
            )

    class UnverifiedError(Exception):
        def __init__(self, discord_id: int):
            self.discord_id = discord_id
            super().__init__(
                f"User {discord_id} is not verified to any Minecraft account."
            )

    async def log_verification(
        self,
        discord_id: int,
        uuid: str,
        source: LinkSource,
        date: datetime.datetime | None = None,
        manual_reason: str | None = None,
    ):
        if manual_reason is not None and source != "manual":
            raise ValueError("manual_reason can only be provided if source is 'manual'")
        if manual_reason is None and source == "manual":
            raise ValueError("manual_reason must be provided if source is 'manual'")
        await self.linked_users_db.update(
            {
                "_id": discord_id,
                "uuid": uuid,
                "source": source,
                "date": date or datetime.datetime.now(),
                "manualReason": manual_reason,
            },
            upsert=True,
        )

    def make_verification_query(
        self, discord_id: int | None = None, uuid: str | None = None
    ) -> dict[str, Any]:
        if discord_id is not None and uuid is None:
            return {"_id": discord_id}
        elif uuid is not None and discord_id is None:
            return {"uuid": uuid}
        elif uuid is not None and discord_id is not None:
            return {"$or": [{"_id": discord_id}, {"uuid": uuid}]}
        else:
            raise ValueError("Either discord_id or uuid must be provided")

    async def search_verification(
        self, discord_id: int | None = None, uuid: str | None = None
    ) -> LinkedUserDoc | None:
        query = self.make_verification_query(discord_id, uuid)
        return await self.linked_users_db.get(query)  # type: ignore

    async def delete_verification(
        self, discord_id: int | None = None, uuid: str | None = None
    ) -> DeleteResult:
        query = self.make_verification_query(discord_id, uuid)
        if query.get("$or"):
            return await self.linked_users_db.delete_many(query)
        return await self.linked_users_db.delete_one(query)

    def get_qualifying_roles(self, player: hypixel.PlayerData) -> list[disnake.Object]:
        roles = [disnake.Object(constants.VERIFIED_ROLE_ID)]
        if player.rank in constants.RANK_ROLES:
            roles.append(disnake.Object(constants.RANK_ROLES[player.rank]))
        return roles

    async def unverify_member(self, member: disnake.Member):
        tasks = []
        to_remove: list[disnake.Role] = [
            role for role in member.roles if role.id in constants.VERIFIED_ONLY_ROLES
        ]
        if to_remove:
            tasks.append(member.remove_roles(*to_remove, reason="Unverified"))
        if member.nick:
            tasks.append(member.edit(nick=None, reason="Unverified"))
        if tasks:
            try:
                await asyncio.gather(*tasks)
            except disnake.errors.Forbidden:
                print(f"Lacking permissions to unverify member: {member.id}")

    async def update_member(
        self,
        member: disnake.Member,
        player: mojang.Player | hypixel.PlayerData | None = None,
    ):
        if player is None:
            doc = await self.search_verification(discord_id=member.id)
            if doc is None:
                return await self.unverify_member(member)
            player = await mojang.get_player(doc["uuid"])
        if isinstance(player, mojang.Player):
            player = await hypixel.get_player(player)

        tasks = []
        reason = f"Verified to {player.uuid}"

        roles = [
            role
            for role in self.get_qualifying_roles(player)
            if not member.get_role(role.id)
        ]
        if roles:
            tasks.append(member.add_roles(*roles, reason=reason))

        if member.display_name != player.name:
            tasks.append(member.edit(nick=player.name, reason=reason))

        if tasks:
            try:
                await asyncio.gather(*tasks)
            except disnake.errors.Forbidden:
                return
                # print(f"Lacking permissions to update member: {member.id}")

    async def hypixel_verify(
        self,
        inter: disnake.AppCmdInter,
        identifier: str,
        member: disnake.Member | None = None,
    ):
        member = member or cast("disnake.Member", inter.author)

        # get mojang playerdata
        player, _ = await asyncio.gather(
            mojang.get_player(identifier),
            inter.response.defer(),
        )

        # make sure they are not already verified or are reverifying the same account
        discord_doc, uuid_doc = await asyncio.gather(
            self.search_verification(discord_id=member.id),
            self.search_verification(uuid=player.uuid),
        )
        if discord_doc and discord_doc["uuid"] != player.uuid:
            verified_to = await mojang.get_player(discord_doc["uuid"])
            raise self.DiscordAlreadyVerifiedError(
                discord_id=member.id,
                verified_to=verified_to,
                attempt_verified_to=player,
            )
        if uuid_doc and uuid_doc["_id"] != member.id:
            raise self.MinecraftAlreadyVerifiedError(
                player=player,
                verified_to=uuid_doc["_id"],
                attempt_verified_to=member.id,
            )

        # ensure discord matches
        data = await hypixel.get_player(player)
        if data.discord != member.name.lower():
            raise self.MismatchedDiscordError(
                expected=member.name.lower(), real=data.discord, identifier=identifier
            )

        # finalize verification
        await asyncio.gather(
            self.log_verification(
                discord_id=member.id,
                uuid=data.uuid,
                source="hypixel",
                date=data.last_updated,
            ),
            self.update_member(member=member, player=data),
        )
        await inter.send(
            embed=self.UtilsCog.make_success(
                title="Verified",
                description="Your Discord account has been verified with your Minecraft account.",
            )
        )

    @commands.slash_command(
        name="verify",
        description="Verify your Discord account with your Minecraft account",
    )
    async def verify_command(
        self,
        inter: disnake.AppCmdInter,
        ign: str = commands.Param(
            description="Your Minecraft username or UUID",
            autocomplete=autocomplete.ign,
            min_length=1,
            max_length=32,
        ),
    ):
        await self.hypixel_verify(inter=inter, identifier=ign)

    @commands.slash_command(
        name="unverify",
        description="Unverify your Discord account from your Minecraft account",
    )
    async def unverify_command(
        self,
        inter: disnake.AppCmdInter,
    ):
        results, _ = await asyncio.gather(
            self.delete_verification(discord_id=inter.author.id), inter.response.defer()
        )
        if not results.deleted_count:
            raise self.UnverifiedError(inter.author.id)
        return await inter.send(
            embed=self.UtilsCog.make_success(
                title="Unverified",
                description="Your Discord account has been unverified from your Minecraft account.",
            )
        )

    @commands.slash_command(
        name="update", description="Update your synced roles and display name"
    )
    async def update_command(
        self,
        inter: disnake.AppCmdInter,
    ):
        await inter.response.defer()
        await self.update_member(member=cast("disnake.Member", inter.author))
        return await inter.send(
            embed=self.UtilsCog.make_success(
                title="Updated",
                description="Your synced roles and display name have been updated.",
            )
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: disnake.Member):
        await self.update_member(member=member)

    async def main(self):
        while True:
            for member in self.UtilsCog.chub.members:
                if member.bot:
                    continue
                try:
                    await self.update_member(member=member)
                except Exception as e:
                    print(f"Error updating member {member.name} ({member.id}): {e}")
                    continue
                await asyncio.sleep(20)
            await asyncio.sleep(60 * 4)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.close()
        self.task = asyncio.create_task(self.main())

    async def close(self):
        if self.task is not None and not self.task.done():
            self.task.cancel()
            self.task = None
        self.linked_users_db.close()
