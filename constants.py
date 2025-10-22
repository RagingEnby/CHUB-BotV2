import scrts

OWNER_IDS: set[int] = {
    447861538095759365,  # RagingEnby
    697136515461152768,  # Vinush
    230778630597246983,  # Thomas
    758304690617712651,  # Foe
}

# URLs
MC_AVATAR_URL: str = "http://cravatar.eu/helmavatar/{}.png"

# Regex
UUID_REGEX: str = (
    r"^(?:[0-9a-fA-F]{32}|[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12})$"
)
USERNAME_REGEX: str = r"^[A-Za-z0-9_]{3,16}$"

# load secrets
BOT_TOKEN: str = scrts.BOT_TOKEN
HYPIXEL_API_KEY: str = scrts.HYPIXEL_API_KEY
PROXY: str = scrts.PROXY
