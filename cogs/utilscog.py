import disnake
from disnake.ext import commands

import constants


def prettify_params(options: disnake.AppCmdInter | dict) -> list[str]:
    if isinstance(options, disnake.AppCmdInter):
        options = options.options
    log_params = []
    for param, value in options.items():
        if isinstance(value, dict):  # if this is a subcommand
            log_params.append(param)
            log_params.extend(prettify_params(value))
        else:
            log_params.append(f"{param}:{value}")
    return log_params


class UtilsCog(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    @property
    def chub(self) -> disnake.Guild:
        guild = self.bot.get_guild(constants.GUILD_ID)
        if guild is None:
            raise ValueError(f"Guild with ID {constants.GUILD_ID} not found")
        return guild

    @staticmethod
    def clean(string: str) -> str:
        return disnake.utils.escape_markdown(disnake.utils.escape_mentions(string))

    @staticmethod
    def prettify_command(inter: disnake.AppCmdInter) -> str:
        return f"/{inter.data.name} {' '.join(prettify_params(inter))}"

    @staticmethod
    def add_guild_footer(
        embed: disnake.Embed, guild: disnake.Guild | None
    ) -> disnake.Embed:
        return embed.set_footer(
            text=f"{guild} ({guild.id})" if guild else "DMs",
            icon_url=guild.icon.url if guild and guild.icon else None,
        )

    @staticmethod
    def add_author_footer(
        embed: disnake.Embed, author: disnake.Member | disnake.User
    ) -> disnake.Embed:
        return embed.set_author(
            name=f"{author} ({author.id})",
            icon_url=author.display_avatar.url,
        )

    @staticmethod
    def inter_to_embed(inter: disnake.AppCmdInter) -> disnake.Embed:
        embed = disnake.Embed(
            title=UtilsCog.prettify_command(inter),
            color=disnake.Color.blurple(),
        )
        embed = UtilsCog.add_author_footer(embed, inter.author)
        return UtilsCog.add_guild_footer(embed, inter.guild)

    @staticmethod
    def message_to_embed(message: disnake.Message) -> disnake.Embed:
        embed = disnake.Embed(
            description=message.content,
            color=disnake.Color.blurple(),
            timestamp=message.created_at,
        )
        embed = UtilsCog.add_author_footer(embed, message.author)
        return UtilsCog.add_guild_footer(embed, message.guild)

    async def send_message(self, channel_id: int, *args, **kwargs) -> disnake.Message:
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            raise ValueError(f"Channel with ID {channel_id} not found")
        if not hasattr(channel, "send"):
            raise ValueError("Channel is not a text channel")
        return await channel.send(*args, **kwargs)  # type: ignore

    async def safe_send_message(
        self, channel_id: int, *args, **kwargs
    ) -> disnake.Message | None:
        try:
            return await self.send_message(channel_id, *args, **kwargs)
        except disnake.HTTPException as e:
            print(f"[UtilsCog] Failed to send message to channel {channel_id}: {e}")
            return await self.safe_send_message(
                channel_id=channel_id,
                content="Tried to send a message but failed (likely over the 2000 char limit). It has been logged to console instead.",
            )

    @staticmethod
    def make_error(title: str, description: str) -> disnake.Embed:
        return disnake.Embed(
            title="❌ Error: " + title,
            description=description,
            color=disnake.Color.red(),
        )

    @staticmethod
    def make_success(title: str, description: str) -> disnake.Embed:
        return disnake.Embed(
            title="✅ " + title,
            description=description,
            color=disnake.Color.green(),
        )

    @staticmethod
    def player_not_found_error(ign: str) -> disnake.Embed:
        clean = UtilsCog.clean(ign)
        return UtilsCog.make_error(
            title="Player Not Found",
            description=f"No Minecraft account with the name [`{clean}`]({constants.NAMEMC_URL.format(clean)}) was found.",
        )

    @staticmethod
    def to_markdown(content: dict[str, str | int | bool | None]) -> str:
        return "\n".join(
            [f"**{k}:** `{str(v).replace('`', '')}`" for k, v in content.items()]
        )
