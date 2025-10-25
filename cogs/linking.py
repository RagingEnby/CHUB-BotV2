import asyncio
from disnake.ext import commands
import disnake
from typing import TYPE_CHECKING, cast, Literal

if TYPE_CHECKING:
    from cogs import UtilsCog
from modules import hypixel, minecraft


class MismatchedDiscordError(Exception):
    def __init__(self, expected: str, real: str | None, identifier: str):
        self.expected = expected
        self.real = real
        self.identifier = identifier
        super().__init__(
            f"Expected Discord username {expected} but got {real} for {identifier}"
        )


class LinkingCog(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot
        self.task: asyncio.Task | None = None

    @property
    def UtilsCog(self) -> "UtilsCog":
        return cast("UtilsCog", self.bot.get_cog("UtilsCog"))

    async def do_hypixel_verify(self, discord_username: str, identifier: str):
        data = await hypixel.get_player(identifier)
        if data.discord != discord_username:
            raise MismatchedDiscordError(discord_username, data.discord, identifier)

    @commands.slash_command(
        name="verify",
        description="Verify your Discord account with your Minecraft account",
    )
    async def verify(self, inter: disnake.AppCmdInter, ign: str):
        await inter.response.defer()
        try:
            await self.do_hypixel_verify(inter.author.name.lower(), ign)
            await inter.send(
                embed=self.UtilsCog.make_success(
                    title="Verification Successful",
                    description="Your Discord account has been verified with your Minecraft account.\n-# (This is a lie and just a test message)",
                )
            )
        except minecraft.PlayerNotFound:
            await inter.send(embed=self.UtilsCog.player_not_found_error(ign))
        except MismatchedDiscordError as e:
            await inter.send(
                embed=self.UtilsCog.make_error(
                    title="Discord Mismatch",
                    description=self.UtilsCog.to_markdown(
                        {
                            "IGN": e.identifier,
                            "Your Discord": e.expected,
                            "Linked Discord": e.real,
                        }
                    ),
                )
            )

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
