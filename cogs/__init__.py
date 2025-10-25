from disnake.ext import commands

from .linking import LinkingCog
from .botstatus import BotStatusCog
from .utilscog import UtilsCog


def load(bot: commands.InteractionBot):
    for cog_name in __all__:
        cog = globals()[cog_name]
        bot.add_cog(cog(bot))


__all__ = [
    "LinkingCog",
    "BotStatusCog",
    "UtilsCog",
]
