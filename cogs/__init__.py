from disnake.ext import commands

from .linking import LinkingCog
from .logger import LoggerCog
from .utilscog import UtilsCog
from .admin import AdminCog


def load(bot: commands.InteractionBot):
    for cog_name in __all__:
        cog = globals()[cog_name]
        bot.add_cog(cog(bot))


__all__ = [
    "LinkingCog",
    "LoggerCog",
    "UtilsCog",
    "AdminCog",
]
