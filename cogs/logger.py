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


def format_error(e: Exception) -> str:
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

    @staticmethod
    def _truncate_block(text: str, limit: int = 1800) -> str:
        return text if len(text) <= limit else text[: limit - 3] + "..."

    def _interaction_title(self, inter: disnake.ApplicationCommandInteraction) -> str:
        try:
            name = inter.data.name  # type: ignore[attr-defined]
        except AttributeError:
            name = None
        return name or "application command"

    def _interaction_to_embed(
        self, inter: disnake.ApplicationCommandInteraction
    ) -> disnake.Embed:
        if isinstance(inter, disnake.AppCmdInter):
            return self.UtilsCog.inter_to_embed(inter)
        embed = disnake.Embed(
            title=self._interaction_title(inter),
            color=disnake.Color.blurple(),
        )
        embed = self.UtilsCog.add_author_footer(embed, inter.author)
        return self.UtilsCog.add_guild_footer(embed, inter.channel)

    async def _send_error_embed(self, embed: disnake.Embed):
        try:
            await self.UtilsCog.send_message(
                channel_id=constants.COMMAND_ERROR_CHANNEL_ID,
                embed=embed,
            )
        except disnake.HTTPException as e:
            print(
                f"[BotStatusCog] Failed to send error to channel {constants.COMMAND_ERROR_CHANNEL_ID}: {e}"
            )
            embed.description = None
            await self.UtilsCog.safe_send_message(
                channel_id=constants.COMMAND_ERROR_CHANNEL_ID,
                embed=embed,
            )

    async def log_interaction_error(
        self, inter: disnake.ApplicationCommandInteraction, e: Exception
    ):
        error = format_error(e)
        print("[BotStatusCog]", error)
        embed = self._interaction_to_embed(inter)
        embed.description = f"```py\n{self._truncate_block(error)}\n```"
        embed.title = "❌ Error: " + (embed.title or "")
        embed.color = disnake.Color.red()
        await self._send_error_embed(embed)

    async def log_message_command_error(self, ctx: commands.Context, e: Exception):
        error = format_error(e)
        print("[BotStatusCog]", error)
        embed = self.UtilsCog.message_to_embed(ctx.message)
        if ctx.command:
            embed.title = ctx.command.qualified_name
        embed.description = (
            f"{embed.description or ''}\n```py\n{self._truncate_block(error)}\n```"
        )
        embed.title = "❌ Error: " + (embed.title or "command")
        embed.color = disnake.Color.red()
        await self._send_error_embed(embed)

    async def log_event_error(self, event: str, error: str, args, kwargs):
        print("[BotStatusCog]", error)
        description = (
            f"**Event:** `{event}`\n"
            f"**Args:** `{self._truncate_block(str(args), 400)}`\n"
            f"**Kwargs:** `{self._truncate_block(str(kwargs), 400)}`\n"
            f"```py\n{self._truncate_block(error)}\n```"
        )
        embed = disnake.Embed(
            title="❌ Error: event handler",
            description=description,
            color=disnake.Color.red(),
        )
        await self._send_error_embed(embed)

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
        self, inter: disnake.ApplicationCommandInteraction, e: commands.CommandError
    ):
        await self.log_interaction_error(inter, e)

    @commands.Cog.listener()
    async def on_message_command_error(
        self, inter: disnake.ApplicationCommandInteraction, e: commands.CommandError
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
