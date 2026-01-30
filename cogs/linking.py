import asyncio
from disnake.ext import commands
import disnake
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from cogs import UtilsCog
from modules import hypixel, autocomplete


class LinkingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.task: asyncio.Task | None = None

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

    async def do_hypixel_verify(self, discord_username: str, identifier: str):
        data = await hypixel.get_player(identifier)
        if data.discord != discord_username:
            raise self.MismatchedDiscordError(
                expected=discord_username, real=data.discord, identifier=identifier
            )

    async def verify(
        self,
        inter: disnake.AppCmdInter,
        identifier: str,
        member: disnake.Member | None = None,
    ):
        member = member or cast("disnake.Member", inter.author)
        await self.do_hypixel_verify(member.name.lower(), identifier)
        await inter.send(
            embed=self.UtilsCog.make_success(
                title="Verification Successful",
                description="Your Discord account has been verified with your Minecraft account.\n-# (This is a lie and just a test message)",
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
            name="ign",
            description="The IGN (in game name) of your Minecraft account",
            default=None,
            autocomplete=autocomplete.ign,
            min_length=1,
            max_length=16,
        ),
    ):
        await inter.response.defer()
        await self.verify(inter=inter, identifier=ign)

    async def main(self):
        while True:
            await asyncio.sleep(30)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.close()
        self.task = asyncio.create_task(self.main())

    async def close(self):
        if self.task is not None and not self.task.done():
            self.task.cancel()
            self.task = None
