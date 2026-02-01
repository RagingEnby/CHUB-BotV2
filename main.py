import asyncio
import signal
import textwrap
import traceback
import unicodedata
from typing import TYPE_CHECKING, cast
import disnake
from disnake.ext import commands

if TYPE_CHECKING:
    from cogs import UtilsCog as UtilsCogType
from modules import asyncreqs
import constants
import cogs


bot = commands.Bot(
    command_prefix=">",
    intents=disnake.Intents(
        automod=False,
        automod_configuration=False,
        automod_execution=False,
        bans=True,
        dm_messages=True,
        dm_reactions=False,
        dm_typing=False,
        emojis=False,
        emojis_and_stickers=False,
        guild_messages=True,
        guild_reactions=False,
        guild_scheduled_events=False,
        guild_typing=False,
        guilds=True,
        integrations=False,
        invites=False,
        members=True,
        message_content=True,
        moderation=True,
        presences=False,
        voice_states=False,
        webhooks=False,
    ),
    owner_ids=constants.OWNER_USER_IDS,
    test_guilds=[constants.GUILD_ID],
)
cogs.load(bot)
UtilsCog: UtilsCogType = cast("UtilsCogType", bot.get_cog("UtilsCog"))


@bot.event
async def on_ready():
    def signal_handler(*_):
        asyncio.create_task(close())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    print(f"Logged in as {bot.user}")


async def close_cog(cog: commands.Cog):
    if hasattr(cog, "close") and callable(cog.close):  # type: ignore
        await cog.close()  # type: ignore


async def close():
    await asyncio.gather(*[close_cog(cog) for cog in bot.cogs.values()])
    print("Cogs closed")
    await asyncreqs.close()
    print("Asyncreqs closed")
    await bot.close()
    print("Bot closed")


# I would put this in a cog but it needs the scope of main.py to be effective for debugging
# this method is stolen from https://github.com/TGWaffles/Utils/blob/4c705ee0855e2a735078b216f8f78bb2143dcbc1/src/cogs/misc.py#L303
# Since you cannot directly execute async code using exec(), we just use exec() to return a
# callable async function and then run that.
@bot.command(
    name="exec",
    aliases=["e", "execute"],
    parent="Admin",
    brief="An admin debugging command allowing you to execute arbitrary code",
    description="An admin debugging command allowing you to execute arbitrary code",
    usage="print('Hello, world!')",
    hidden=True,
)
async def exec_cmd(inter: commands.Context, *, code: str = ""):
    if not await bot.is_owner(inter.author):
        return await inter.send(
            embed=UtilsCog.make_error(
                title="Unauthorized",
                description="You do not have permission to use this command.",
            )
        )
    try:
        tmp_dic = {}
        raw = (
            (code or inter.message.content.partition(" ")[2])
            .replace("”", '"')
            .replace("’", "'")
            .replace("‘", "'")
        )
        raw = "".join(
            ch
            for ch in raw
            if ch in "\n\t" or not unicodedata.category(ch).startswith("C")
        )
        if raw.startswith("```"):
            raw = raw.partition("\n")[2].rsplit("```", 1)[0]
        body = raw.strip("`\n ")
        executing_string = f"async def temp_func():\n{textwrap.indent(body, '    ')}\n"
        print("executing_string", executing_string)
        exec(executing_string, {**globals(), **locals()}, tmp_dic)
        await tmp_dic["temp_func"]()
        await inter.message.add_reaction("✅")
    except:  # noqa: E722
        error = traceback.format_exc()
        print("exec error:", error)
        await asyncio.gather(
            inter.message.add_reaction("❌"),
            inter.send(
                embed=UtilsCog.make_error(
                    title="Code Execution Error", description=f"```py\n{error}```"
                )
            ),
        )


if __name__ == "__main__":
    bot.run(constants.BOT_TOKEN)
