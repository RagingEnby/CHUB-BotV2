import asyncio
import datetime
import disnake
from disnake.ext import commands
import traceback
from contextlib import suppress
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from cogs import UtilsCog, LinkingCog
from modules import mojang, hypixel
import constants


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

    @staticmethod
    def format_error(e: Exception) -> str:
        return "".join(traceback.format_exception(type(e), e, e.__traceback__))

    @staticmethod
    def _truncate_block(text: str, limit: int = 1800) -> str:
        return text if len(text) <= limit else text[: limit - 3] + "..."

    async def _send_error_embed(self, embed: disnake.Embed):
        try:
            await self.UtilsCog.send_message(
                content=f"<@{constants.DEVELOPER_ID}>",
                channel_id=constants.COMMAND_ERROR_CHANNEL_ID,
                embed=embed,
            )
        except disnake.HTTPException as e:
            print(
                f"[LoggerCog] Failed to send error to channel {constants.COMMAND_ERROR_CHANNEL_ID}: {e}"
            )
            embed.description = None
            await self.UtilsCog.safe_send_message(
                channel_id=constants.COMMAND_ERROR_CHANNEL_ID,
                embed=embed,
            )

    async def log_error(self, e: Exception | str, embed: disnake.Embed | None = None):
        error = self.format_error(e) if isinstance(e, Exception) else e
        print("[LoggerCog]", e)
        embed = embed or disnake.Embed(title=str(e), color=disnake.Color.red())
        embed.title = "❌ Error: " + (embed.title or "")
        embed.description = f"```py\n{self._truncate_block(error), 1800 - len(embed.description or '')}\n```"
        await self._send_error_embed(embed)

    async def log_interaction_error(self, inter: disnake.AppCmdInter, e: Exception):
        await self.log_error(e=e, embed=self.UtilsCog.inter_to_embed(inter))

    async def log_message_command_error(self, ctx: commands.Context, e: Exception):
        embed = self.UtilsCog.message_to_embed(ctx.message)
        if ctx.command:
            embed.title = ctx.command.qualified_name
        await self.log_error(e=e, embed=embed)

    async def log_event_error(self, event: str, error: str, args, kwargs):
        print(f"event={event}\nargs={args}\nkwargs={kwargs}")
        await self.log_error(
            e=self._truncate_block(error, 25),
            embed=disnake.Embed(
                title=f"[{event}] event handler",
                description=self.UtilsCog.to_markdown(
                    {
                        "Event": event,
                        "Args": self._truncate_block(str(args), 400),
                        "Kwargs": self._truncate_block(str(kwargs), 400),
                    }
                ),
            ),
        )

    @commands.Cog.listener()
    async def on_slash_command_error(
        self, inter: disnake.AppCmdInter, e: commands.CommandError
    ):
        with suppress(disnake.InteractionResponded, disnake.HTTPException):
            await inter.response.defer(ephemeral=True)
        error = (
            cast("Exception", e.original)  # type: ignore
            if hasattr(e, "original")
            else cast("Exception", e)
        )

        if isinstance(error, commands.CheckFailure):
            error = cast("commands.CheckFailure", error)
            return await inter.send(
                embed=self.UtilsCog.make_error(
                    title="Unauthorized",
                    description="You do not have permission to use this command.",
                )
            )

        if isinstance(error, commands.CommandOnCooldown):
            error = cast("commands.CommandOnCooldown", error)
            try_at = datetime.datetime.now() + datetime.timedelta(
                seconds=error.retry_after
            )
            return await inter.send(
                embed=self.UtilsCog.make_error(
                    title="Cooldown",
                    description=f"Try again {disnake.utils.format_dt(try_at, 'R')}.",
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

        if isinstance(error, self.LinkingCog.DiscordAlreadyVerifiedError):
            error = cast("LinkingCog.DiscordAlreadyVerifiedError", error)
            return await inter.send(
                embed=self.UtilsCog.make_error(
                    title="Already Verified",
                    description=f"You are already verified to [{error.verified_to.name}]({constants.NAMEMC_URL.format(error.verified_to.uuid)}), you cannot verify to two accounts at once. Please use `/unverify` and try again.",
                )
            )

        if isinstance(error, self.LinkingCog.MinecraftAlreadyVerifiedError):
            error = cast("LinkingCog.MinecraftAlreadyVerifiedError", error)
            return await inter.send(
                embed=self.UtilsCog.make_error(
                    title="Already Verified",
                    description=f"Player [{error.player.name}]({constants.NAMEMC_URL.format(error.player.uuid)}) is already verified to <@{error.verified_to}>. The same Minecraft account cannot be verified to two Discord accounts.",
                )
            )

        if isinstance(error, self.LinkingCog.UnverifiedError):
            error = cast("LinkingCog.UnverifiedError", error)
            return await inter.send(
                embed=self.UtilsCog.make_error(
                    title="Not Verified",
                    description="This command is only accessible to verified users. Please use `/verify` and try again.",
                )
            )

        if isinstance(error, hypixel.RateLimitError):
            error = cast("hypixel.RateLimitError", error)
            return await inter.send(
                embed=self.UtilsCog.make_error(
                    title="Hypixel Rate Limit",
                    description=f"Hypixel is currently rate limiting our API key, please try again {disnake.utils.format_dt(datetime.datetime.now() + error.retry, 'R')}.",
                )
            )

        if isinstance(error, commands.MemberNotFound):
            error = cast("commands.MemberNotFound", error)
            return await inter.send(
                embed=self.UtilsCog.make_error(
                    title="Member Not Found",
                    description=f"The member you are trying to target was not found (`{error.argument}`)",
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
            self.log_interaction_error(inter, e),
        )

    @commands.Cog.listener()
    async def on_user_command_error(
        self, inter: disnake.AppCmdInter, e: commands.CommandError
    ):
        await self.log_interaction_error(inter, e)

    @commands.Cog.listener()
    async def on_message_command_error(
        self, inter: disnake.AppCmdInter, e: commands.CommandError
    ):
        await self.log_interaction_error(inter, e)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, e: commands.CommandError):
        await self.log_message_command_error(ctx, e)

    @commands.Cog.listener()
    async def on_error(self, event: str, *args, **kwargs):
        error = traceback.format_exc()
        await self.log_event_error(event, error, args, kwargs)

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
            f"[LoggerCog] {inter.author} used {self.UtilsCog.prettify_command(inter)}"
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
