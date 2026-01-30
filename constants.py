import scrts

# Secrets
BOT_TOKEN: str = scrts.BOT_TOKEN
HYPIXEL_API_KEY: str = scrts.HYPIXEL_API_KEY
PROXY: str = scrts.PROXY

# Discord IDs
## Users
OWNER_USER_IDS: set[int] = {
    447861538095759365,  # RagingEnby
    697136515461152768,  # Vinush
    230778630597246983,  # Thomas
    758304690617712651,  # Foe
}

ADMIN_IGNS: set[str] = {"RagingEnby", "Vinush", "TGWaffles", "_Foe", "t3ferrari"}
## Channels
COMMAND_ERROR_CHANNEL_ID: int = 1431767322401444010
COMMAND_LOG_CHANNEL_ID: int = 1431781003533222038
BOT_STATUS_CHANNEL_ID: int = 1431777398797500426
DM_LOG_CHANNEL_ID: int = 1466599169358696538
## Guilds
GUILD_ID: int = 1430328872465076417

# URLs
MC_AVATAR_URL: str = "http://cravatar.eu/helmavatar/{}.png"
NAMEMC_URL: str = "https://nmc.is/{}"
MOJANG_API_URL: str = "https://mowojang.matdoes.dev/{}"
IGN_STEM_URL: str = "https://api.ragingenby.dev/stem/{}"

# Regex
UUID_REGEX: str = (
    r"^(?:[0-9a-fA-F]{32}|[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12})$"
)
USERNAME_REGEX: str = r"^[A-Za-z0-9_]{3,16}$"
