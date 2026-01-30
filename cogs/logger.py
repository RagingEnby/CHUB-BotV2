import asyncio
import disnake
from disnake.ext import commands
import traceback
from contextlib import suppress
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from cogs import UtilsCog, LinkingCog
from modules import mojang
import constants


def format_error(e: commands.CommandError) -> str:
    return "".join(traceback.format_exception(type(e), e, e.__traceback__))


class LoggerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.first_start = True
        self.task: asyncio.Task | None = None

    @property
    def UtilsCog(self) -> "UtilsCog":
        return cast("UtilsCog", self.bot.get_cog("UtilsCog"))

    @property
    def LinkingCog(self) -> "LinkingCog":
        return cast("LinkingCog", self.bot.get_cog("LinkingCog"))

    async def log_command_error(
        self, inter: disnake.AppCmdInter, e: commands.CommandError
    ):
        error = format_error(e)
        print("[BotStatusCog]", error)
        embed = self.UtilsCog.inter_to_embed(inter)
        embed.description = f"```py\n{error[:2000]}\n```"
        embed.title = "❌ Error: " + (embed.title or "")
        embed.color = disnake.Color.red()
        try:
            await self.UtilsCog.send_message(
                channel_id=constants.COMMAND_ERROR_CHANNEL_ID,
                embed=embed,
            )
        except disnake.HTTPException:
            print(
                f"[BotStatusCog] Failed to send command error to channel {constants.COMMAND_ERROR_CHANNEL_ID}: {e}"
            )
            embed.description = None
            await self.UtilsCog.safe_send_message(
                channel_id=constants.COMMAND_ERROR_CHANNEL_ID,
                embed=embed,
            )

    @commands.Cog.listener()
    async def on_slash_command_error(
        self, inter: disnake.AppCmdInter, e: commands.CommandError
    ):
        with suppress(disnake.InteractionResponded):
            await inter.response.defer(ephemeral=True)
        error = cast("Exception", e.original)  # type: ignore

        if isinstance(e, commands.CheckFailure):
            return await inter.send(
                embed=self.UtilsCog.make_error(
                    title="Unauthorized",
                    description="You do not have permission to use this command.",
                )
            )

        if isinstance(error, mojang.PlayerNotFound):
            error = cast("mojang.PlayerNotFound", error)
            return await inter.send(
                embed=self.UtilsCog.player_not_found_error(error.identifier)
            )

        if isinstance(error, self.LinkingCog.MismatchedDiscordError):
            error = cast("LinkingCog.MismatchedDiscordError", error)
            return await inter.send(
                embed=self.UtilsCog.make_error(
                    title="Discord Mismatch",
                    description=self.UtilsCog.to_markdown(
                        {
                            "IGN": error.identifier,
                            "Your Discord": error.expected,
                            "Linked Discord": error.real,
                        }
                    ),
                )
            )

        if isinstance(error, self.LinkingCog.AlreadyVerifiedError):
            error = cast("LinkingCog.AlreadyVerifiedError", error)
            return await inter.send(
                embed=self.UtilsCog.make_error(
                    title="Already Verified",
                    description=f"You are already verified to [{error.verified_to}]({constants.NAMEMC_URL.format(error.verified_to)}), you cannot verify to two accounts at once. Please use `/unverify` and try again.",
                )
            )

        # Unknown errors
        await asyncio.gather(
            inter.send(
                embed=self.UtilsCog.make_error(
                    title="An Unknown Error Occurred",
                    description="This error has been forwarded to the bot developer. Please try again later.",
                )
            ),
            self.log_command_error(inter, e),
        )

    @commands.Cog.listener()
    async def on_error(self, event: str, *args, **kwargs):
        print(f"[BotStatusCog] Error in {event}: {args} {kwargs}")

    async def close(self):
        await self.UtilsCog.send_message(
            channel_id=constants.BOT_STATUS_CHANNEL_ID,
            embed=disnake.Embed(
                title="Bot Closing...",
                color=disnake.Color.red(),
            ),
        )

    @commands.Cog.listener()
    async def on_slash_command(self, inter: disnake.AppCmdInter):
        print(
            f"[BotStatusCog] {inter.author} used {self.UtilsCog.prettify_command(inter)}"
        )

    @commands.Cog.listener()
    async def on_slash_command_completion(self, inter: disnake.AppCmdInter):
        response = await inter.original_response()
        embeds = [self.UtilsCog.inter_to_embed(inter)]
        if response.content:
            embeds.append(self.UtilsCog.message_to_embed(response))
        embeds.extend(response.embeds)
        await self.UtilsCog.safe_send_message(
            channel_id=constants.COMMAND_LOG_CHANNEL_ID,
            embeds=embeds,
        )

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        # only log DMs from humans
        if message.guild or message.author.bot:
            return
        await self.UtilsCog.safe_send_message(
            channel_id=constants.DM_LOG_CHANNEL_ID,
            embed=self.UtilsCog.message_to_embed(message),
        )

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.first_start:
            return
        self.first_start = False
        await self.UtilsCog.send_message(
            constants.BOT_STATUS_CHANNEL_ID,
            embed=disnake.Embed(
                title="Bot Starting...",
                color=disnake.Color.green(),
            ),
        )
