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
    def __init__(self, bot: commands.Bot):
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
        embed: disnake.Embed, channel: disnake.abc.MessageableChannel
    ) -> disnake.Embed:
        text = "DMs"
        icon_url = None
        if hasattr(channel, "guild") and channel.guild:  # type: ignore
            text = f"{channel.guild} #{channel.name}"  # type: ignore
            if channel.guild.icon:  # type: ignore
                icon_url = channel.guild.icon.url  # type: ignore
        return embed.set_footer(text=text, icon_url=icon_url)

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
        return UtilsCog.add_guild_footer(embed, inter.channel)

    @staticmethod
    def message_to_embed(message: disnake.Message) -> disnake.Embed:
        embed = disnake.Embed(
            description=message.content,
            color=disnake.Color.blurple(),
            timestamp=message.created_at,
        )
        embed = UtilsCog.add_author_footer(embed, message.author)
        return UtilsCog.add_guild_footer(embed, message.channel)

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

    async def dm(
        self, user: disnake.User | disnake.Member | int, *args, **kwargs
    ) -> disnake.Message:
        user_id = user if isinstance(user, int) else user.id
        user_obj = self.chub.get_member(user_id)
        if user_obj is None:
            raise ValueError(f"User with ID {user_id} not found")
        return await user_obj.send(*args, **kwargs)

    async def safe_dm(
        self, user: disnake.User | disnake.Member | int, *args, **kwargs
    ) -> disnake.Message | None:
        try:
            return await self.dm(user, *args, **kwargs)
        except (
            disnake.HTTPException,
            disnake.NotFound,
            ValueError,
            commands.MemberNotFound,
        ) as e:
            print(
                f"[UtilsCog] Failed to send DM to user {user if isinstance(user, int) else user.id}: {e}"
            )
            return None

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
    def to_markdown(content: dict[str, str | int | bool | None], block: bool = True) -> str:
        return "\n".join(
            [f"**{k}:** {f'`{str(v).replace('`', '')}`' if block else str(v)}" for k, v in content.items()]
        )

    def is_staff(self, member: disnake.Member | disnake.User | int) -> bool:
        if isinstance(member, disnake.Member) and member.guild.id == constants.GUILD_ID:
            return member.get_role(constants.STAFF_ROLE_ID) is not None
        chub_member = self.chub.get_member(
            member if isinstance(member, int) else member.id
        )
        return (
            chub_member is not None
            and chub_member.get_role(constants.STAFF_ROLE_ID) is not None
        )
