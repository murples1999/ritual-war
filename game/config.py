"""Game configuration constants and settings."""

THRESHOLD = 12
SHIELD_CLEANSE = 2
SIGNATURE_TTL_HOURS = 24
VEIL_REDUCTION = 0.5
TIMEZONE = "America/Los_Angeles"

FRESH_BUCKETS = [
    (0, 6, "Fresh"),
    (6, 18, "Warm"), 
    (18, 24, "Cooling")
]

DATABASE_PATH = "ritual_war.db"

# Channel configuration
RITUAL_WAR_CHANNEL_ID = 1409497777775448074  # Only public messages go here
XP_REWARD_AMOUNT = 100  # XP to award for victory