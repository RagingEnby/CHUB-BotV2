import disnake
from disnake.ext import commands

import constants


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
    owner_ids=constants.OWNER_IDS,
)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


if __name__ == "__main__":
    bot.run(constants.BOT_TOKEN)
