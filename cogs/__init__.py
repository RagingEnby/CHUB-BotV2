from disnake.ext import commands

from .linking import LinkingCog
from .logger import LoggerCog
from .utils import UtilsCog
from .admin import AdminCog
from .moderation import ModerationCog


def load(bot: commands.Bot):
    for cog_name in __all__:
        cog = globals()[cog_name]
        bot.add_cog(cog(bot))


__all__ = [
    "LinkingCog",
    "LoggerCog",
    "UtilsCog",
    "AdminCog",
    "ModerationCog",
]
