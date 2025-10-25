import asyncio
import disnake
from disnake.ext import commands
import signal

from modules import asyncreqs
import constants
import cogs


bot = commands.InteractionBot(
    intents=disnake.Intents(
        automod=False,
        automod_configuration=False,
        automod_execution=False,
        bans=True,
        dm_messages=True,
        dm_reactions=False,
        dm_typing=False,
        emojis=True,
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


if __name__ == "__main__":
    bot.run(constants.BOT_TOKEN)
