"""Data models for the Ritual War game."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Player:
    """Represents a player in the game."""
    user_id: str
    guild_id: str
    joined_at: int
    doom: int
    veil_until: Optional[int]
    last_action_day: Optional[str]
    active: int


@dataclass
class Signature:
    """Represents a Hex or Mend signature on a target."""
    target_id: str
    signer_id: str
    guild_id: str
    type: str  # 'hex' or 'mend'
    expires_at: int


@dataclass
class Claim:
    """Represents a public claim on a target's train."""
    target_id: str
    guild_id: str
    type: str  # 'hex' or 'mend'
    claimant_id: str
    expires_at: int


@dataclass
class TrainStatus:
    """Status of a signature train on a target."""
    count: int
    freshness: str


@dataclass
class PlayerStatus:
    """Public status of a player."""
    user_id: str
    doom: int
    hex_train: TrainStatus
    mend_train: TrainStatus
    veil_hours_remaining: Optional[float] = None  # Only for self inspection


@dataclass
class ActionResult:
    """Result of performing a game action."""
    success: bool
    message: str
    public_message: Optional[str] = None
    doom_change: Optional[int] = None
    new_doom: Optional[int] = None
    eliminated: bool = False
    reflex_shield_triggered: bool = False
    winner_id: Optional[str] = None