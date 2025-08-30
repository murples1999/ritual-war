"""Database storage layer for Ritual War."""

import aiosqlite
from typing import List, Optional, Dict, Any
from .models import Player, Signature, Claim
from .config import DATABASE_PATH
from .timeutils import now


class GameStorage:
    """Handles all database operations for the game."""
    
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
    
    async def initialize(self):
        """Initialize the database with required tables."""
        async with aiosqlite.connect(self.db_path) as db:
            # Check if guild_id column exists in players table
            cursor = await db.execute("PRAGMA table_info(players)")
            columns = await cursor.fetchall()
            has_guild_id = any(col[1] == 'guild_id' for col in columns)
            
            if not has_guild_id:
                # Create new table with guild_id
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS players (
                        user_id TEXT NOT NULL,
                        guild_id TEXT NOT NULL,
                        joined_at INTEGER NOT NULL,
                        doom INTEGER NOT NULL DEFAULT 0,
                        veil_until INTEGER,
                        last_action_day TEXT,
                        active INTEGER NOT NULL DEFAULT 1,
                        PRIMARY KEY(user_id, guild_id)
                    )
                """)
                
                # Migrate existing data if old table exists
                try:
                    await db.execute("""
                        INSERT INTO players (user_id, guild_id, joined_at, doom, veil_until, last_action_day, active)
                        SELECT user_id, 'LEGACY_GUILD', joined_at, doom, veil_until, last_action_day, active
                        FROM players_backup
                    """)
                except:
                    # No existing data to migrate
                    pass
            else:
                # Table already has guild_id, ensure it exists
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS players (
                        user_id TEXT NOT NULL,
                        guild_id TEXT NOT NULL,
                        joined_at INTEGER NOT NULL,
                        doom INTEGER NOT NULL DEFAULT 0,
                        veil_until INTEGER,
                        last_action_day TEXT,
                        active INTEGER NOT NULL DEFAULT 1,
                        PRIMARY KEY(user_id, guild_id)
                    )
                """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS signatures (
                    target_id TEXT NOT NULL,
                    signer_id TEXT NOT NULL,
                    guild_id TEXT NOT NULL,
                    type TEXT NOT NULL CHECK(type IN ('hex','mend')),
                    expires_at INTEGER NOT NULL,
                    PRIMARY KEY(target_id, signer_id, guild_id, type)
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS claims (
                    target_id TEXT NOT NULL,
                    guild_id TEXT NOT NULL,
                    type TEXT NOT NULL CHECK(type IN ('hex','mend')),
                    claimant_id TEXT NOT NULL,
                    expires_at INTEGER NOT NULL,
                    PRIMARY KEY(target_id, guild_id, type, claimant_id)
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS state (
                    guild_id TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    PRIMARY KEY(guild_id, key)
                )
            """)
            
            await db.commit()
    
    async def migrate_legacy_data(self, guild_id: str):
        """Migrate existing data to the new guild-aware format."""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                # Check if we need to migrate by looking for old table structure
                cursor = await db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='players'")
                table_sql = await cursor.fetchone()
                
                if table_sql and 'guild_id' not in table_sql[0]:
                    # Backup old table
                    await db.execute("ALTER TABLE players RENAME TO players_old")
                    await db.execute("ALTER TABLE signatures RENAME TO signatures_old")
                    await db.execute("ALTER TABLE claims RENAME TO claims_old")
                    await db.execute("ALTER TABLE state RENAME TO state_old")
                    
                    # Recreate tables with new structure
                    await self.initialize()
                    
                    # Migrate data
                    await db.execute("""
                        INSERT INTO players (user_id, guild_id, joined_at, doom, veil_until, last_action_day, active)
                        SELECT user_id, ?, joined_at, doom, veil_until, last_action_day, active
                        FROM players_old
                    """, (guild_id,))
                    
                    await db.execute("""
                        INSERT INTO signatures (target_id, signer_id, guild_id, type, expires_at)
                        SELECT target_id, signer_id, ?, type, expires_at
                        FROM signatures_old
                    """, (guild_id,))
                    
                    await db.execute("""
                        INSERT INTO claims (target_id, guild_id, type, claimant_id, expires_at)
                        SELECT target_id, ?, type, claimant_id, expires_at
                        FROM claims_old
                    """, (guild_id,))
                    
                    await db.execute("""
                        INSERT INTO state (guild_id, key, value)
                        SELECT ?, key, value
                        FROM state_old
                    """, (guild_id,))
                    
                    # Clean up old tables
                    await db.execute("DROP TABLE players_old")
                    await db.execute("DROP TABLE signatures_old")
                    await db.execute("DROP TABLE claims_old")
                    await db.execute("DROP TABLE state_old")
                    
                    await db.commit()
                    
            except Exception:
                # Migration not needed or already done
                pass
    
    async def purge_expired(self, guild_id: str):
        """Remove expired signatures and claims for a guild."""
        current_time = int(now().timestamp())
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM signatures WHERE guild_id = ? AND expires_at <= ?", (guild_id, current_time))
            await db.execute("DELETE FROM claims WHERE guild_id = ? AND expires_at <= ?", (guild_id, current_time))
            await db.commit()
    
    async def get_player(self, user_id: str, guild_id: str) -> Optional[Player]:
        """Get a player by user ID and guild ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM players WHERE user_id = ? AND guild_id = ?", (user_id, guild_id)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return Player(**dict(row))
                return None
    
    async def get_active_players(self, guild_id: str) -> List[Player]:
        """Get all active players in a guild."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM players WHERE guild_id = ? AND active = 1", (guild_id,)) as cursor:
                rows = await cursor.fetchall()
                return [Player(**dict(row)) for row in rows]
    
    async def create_player(self, user_id: str, guild_id: str) -> Player:
        """Create a new player."""
        joined_at = int(now().timestamp())
        player = Player(
            user_id=user_id,
            guild_id=guild_id,
            joined_at=joined_at,
            doom=0,
            veil_until=None,
            last_action_day=None,
            active=1
        )
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO players (user_id, guild_id, joined_at, doom, veil_until, last_action_day, active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (player.user_id, player.guild_id, player.joined_at, player.doom, player.veil_until, player.last_action_day, player.active))
            await db.commit()
        
        return player
    
    async def update_player(self, player: Player):
        """Update a player's data."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE players 
                SET doom = ?, veil_until = ?, last_action_day = ?, active = ?
                WHERE user_id = ? AND guild_id = ?
            """, (player.doom, player.veil_until, player.last_action_day, player.active, player.user_id, player.guild_id))
            await db.commit()
    
    async def get_signatures(self, target_id: str, sig_type: str, guild_id: str) -> List[Signature]:
        """Get all signatures of a specific type on a target in a guild."""
        await self.purge_expired(guild_id)
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM signatures WHERE target_id = ? AND type = ? AND guild_id = ?", 
                (target_id, sig_type, guild_id)
            ) as cursor:
                rows = await cursor.fetchall()
                return [Signature(**dict(row)) for row in rows]
    
    async def has_signature(self, target_id: str, signer_id: str, sig_type: str, guild_id: str) -> bool:
        """Check if a signer has an active signature of a type on a target in a guild."""
        await self.purge_expired(guild_id)
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM signatures WHERE target_id = ? AND signer_id = ? AND type = ? AND guild_id = ?",
                (target_id, signer_id, sig_type, guild_id)
            ) as cursor:
                count = await cursor.fetchone()
                return count[0] > 0
    
    async def add_signature(self, signature: Signature):
        """Add or refresh a signature."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO signatures (target_id, signer_id, guild_id, type, expires_at)
                VALUES (?, ?, ?, ?, ?)
            """, (signature.target_id, signature.signer_id, signature.guild_id, signature.type, signature.expires_at))
            await db.commit()
    
    async def clear_signatures(self, user_id: str, guild_id: str):
        """Clear all signatures for a user in a guild (when they leave)."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM signatures WHERE signer_id = ? AND guild_id = ?", (user_id, guild_id))
            await db.commit()
    
    async def get_claims(self, target_id: str, claim_type: str, guild_id: str) -> List[Claim]:
        """Get all claims of a specific type on a target in a guild."""
        await self.purge_expired(guild_id)
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM claims WHERE target_id = ? AND type = ? AND guild_id = ?",
                (target_id, claim_type, guild_id)
            ) as cursor:
                rows = await cursor.fetchall()
                return [Claim(**dict(row)) for row in rows]
    
    async def add_claim(self, claim: Claim):
        """Add a claim."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO claims (target_id, guild_id, type, claimant_id, expires_at)
                VALUES (?, ?, ?, ?, ?)
            """, (claim.target_id, claim.guild_id, claim.type, claim.claimant_id, claim.expires_at))
            await db.commit()
    
    async def remove_claim(self, target_id: str, claim_type: str, claimant_id: str, guild_id: str):
        """Remove a claim."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM claims WHERE target_id = ? AND type = ? AND claimant_id = ? AND guild_id = ?",
                (target_id, claim_type, claimant_id, guild_id)
            )
            await db.commit()
    
    async def clear_claims(self, user_id: str, guild_id: str):
        """Clear all claims for a user in a guild (when they leave)."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM claims WHERE claimant_id = ? AND guild_id = ?", (user_id, guild_id))
            await db.commit()
    
    async def get_state(self, key: str, guild_id: str) -> Optional[str]:
        """Get a state value for a guild."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT value FROM state WHERE key = ? AND guild_id = ?", (key, guild_id)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None
    
    async def set_state(self, key: str, value: str, guild_id: str):
        """Set a state value for a guild."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO state (guild_id, key, value) VALUES (?, ?, ?)",
                (guild_id, key, value)
            )
            await db.commit()
    
    async def is_roster_locked(self, guild_id: str) -> bool:
        """Check if the roster is locked (after first elimination) for a guild."""
        locked = await self.get_state("roster_locked", guild_id)
        return locked == "1"
    
    async def lock_roster(self, guild_id: str):
        """Lock the roster after first elimination for a guild."""
        await self.set_state("roster_locked", "1", guild_id)
    
    async def get_user_lockouts(self, user_id: str, guild_id: str) -> Dict[str, List[str]]:
        """Get targets that a user cannot hex/mend due to active signatures in a guild."""
        await self.purge_expired(guild_id)
        
        lockouts = {"hex": [], "mend": []}
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT target_id, type FROM signatures WHERE signer_id = ? AND guild_id = ?",
                (user_id, guild_id)
            ) as cursor:
                rows = await cursor.fetchall()
                for target_id, sig_type in rows:
                    lockouts[sig_type].append(target_id)
        
        return lockouts
    
    async def clear_all_game_data(self, guild_id: str):
        """Clear all game data for a guild for a fresh start."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM players WHERE guild_id = ?", (guild_id,))
            await db.execute("DELETE FROM signatures WHERE guild_id = ?", (guild_id,)) 
            await db.execute("DELETE FROM claims WHERE guild_id = ?", (guild_id,))
            await db.execute("DELETE FROM state WHERE guild_id = ?", (guild_id,))
            await db.commit()