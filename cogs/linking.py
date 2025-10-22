from disnake.ext import commands


class LinkingCog(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"[LinkingCog] Logged in as {self.bot.user}")

    async def close(self):
        print("[LinkingCog] Closing cog...")
