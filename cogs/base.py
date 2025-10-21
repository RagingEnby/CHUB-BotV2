"""BASE COG - NOT FOR USAGE"""

from disnake.ext import commands


class BaseCog(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"[BaseCog] Logged in as {self.bot.user}")

    async def close(self):
        print("[BaseCog] Closing cog...")
