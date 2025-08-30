"""Core game logic for Ritual War."""

import math
from typing import Tuple
from .models import Player, Signature, ActionResult, TrainStatus
from .storage import GameStorage
from .timeutils import now, today_key, timestamp_from_hours, hours_since, get_freshness_bucket, hours_until
from .config import THRESHOLD, SHIELD_CLEANSE, SIGNATURE_TTL_HOURS, VEIL_REDUCTION


class GameLogic:
    """Handles all game logic operations."""
    
    def __init__(self, storage: GameStorage, guild_id: str):
        self.storage = storage
        self.guild_id = guild_id
    
    async def can_join_game(self) -> Tuple[bool, str]:
        """Check if a player can join the game."""
        if await self.storage.is_roster_locked(self.guild_id):
            return False, "The roster is locked. No new players can join after the first elimination."
        return True, ""
    
    async def join_game(self, user_id: str) -> ActionResult:
        """Have a player join the game."""
        existing = await self.storage.get_player(user_id, self.guild_id)
        if existing and existing.active:
            return ActionResult(False, "You are already in the game!")
        
        can_join, reason = await self.can_join_game()
        if not can_join:
            return ActionResult(False, reason)
        
        if existing:
            existing.active = 1
            existing.doom = 0
            existing.veil_until = None
            existing.last_action_day = None
            await self.storage.update_player(existing)
        else:
            await self.storage.create_player(user_id, self.guild_id)
        
        return ActionResult(
            True,
            "You have joined the Ritual War! Use `/leaderboard` to see the current state.",
            f"<@{user_id}> has joined the Ritual War!"
        )
    
    async def leave_game(self, user_id: str) -> ActionResult:
        """Have a player leave the game."""
        player = await self.storage.get_player(user_id, self.guild_id)
        if not player or not player.active:
            return ActionResult(False, "You are not in the game.")
        
        player.active = 0
        await self.storage.update_player(player)
        await self.storage.clear_signatures(user_id, self.guild_id)
        await self.storage.clear_claims(user_id, self.guild_id)
        
        return ActionResult(
            True,
            "You have left the Ritual War.",
            f"<@{user_id}> has left the Ritual War!"
        )
    
    async def get_train_status(self, target_id: str, sig_type: str) -> TrainStatus:
        """Get the status of a signature train on a target."""
        signatures = await self.storage.get_signatures(target_id, sig_type, self.guild_id)
        count = len(signatures)
        
        if count == 0:
            return TrainStatus(0, "Expired")
        
        # Get oldest signature to determine freshness
        oldest_hours = min(hours_since(sig.expires_at - SIGNATURE_TTL_HOURS * 3600) for sig in signatures)
        freshness = get_freshness_bucket(oldest_hours)
        
        return TrainStatus(count, freshness)
    
    async def can_act_today(self, user_id: str, bypass_daily_limit: bool = False) -> Tuple[bool, str]:
        """Check if a player can act today."""
        player = await self.storage.get_player(user_id, self.guild_id)
        if not player or not player.active:
            return False, "You are not in the game."
        
        # Bypass daily limit for testing (admin simulate actions)
        if bypass_daily_limit:
            return True, ""
        
        today = today_key()
        if player.last_action_day == today:
            return False, "You have already acted today. Wait until tomorrow to act again."
        
        return True, ""
    
    async def hex_target(self, actor_id: str, target_id: str, bypass_daily_limit: bool = False) -> ActionResult:
        """Execute a Hex action."""
        if actor_id == target_id:
            return ActionResult(False, "You cannot target yourself with Hex.")
        
        actor = await self.storage.get_player(actor_id, self.guild_id)
        target = await self.storage.get_player(target_id, self.guild_id)
        
        if not actor or not actor.active:
            return ActionResult(False, "You are not in the game.")
        
        if not target or not target.active:
            return ActionResult(False, "Target is not in the game.")
        
        can_act, reason = await self.can_act_today(actor_id, bypass_daily_limit)
        if not can_act:
            return ActionResult(False, reason)
        
        if await self.storage.has_signature(target_id, actor_id, "hex", self.guild_id):
            return ActionResult(False, "You already have an active Hex signature on this target.")
        
        # Get current mark status
        hex_train = await self.get_train_status(target_id, "hex")
        mend_train = await self.get_train_status(target_id, "mend")
        
        # Calculate raw damage
        raw_damage = 1 + hex_train.count
        
        # Check if target would be eliminated and needs Reflex Shield
        reflex_shield_triggered = False
        if target.doom + raw_damage >= THRESHOLD:
            target_can_act, _ = await self.can_act_today(target_id)
            if target_can_act:
                # Trigger Reflex Shield
                reflex_shield_triggered = True
                target.doom = max(0, target.doom - SHIELD_CLEANSE)
                target.veil_until = timestamp_from_hours(SIGNATURE_TTL_HOURS)
                target.last_action_day = today_key()
                await self.storage.update_player(target)
        
        # Calculate final damage with Veil
        final_damage = raw_damage
        veil_active = target.veil_until and target.veil_until > int(now().timestamp())
        if veil_active:
            final_damage = math.floor(raw_damage * VEIL_REDUCTION)
        
        # Apply damage
        target.doom += final_damage
        eliminated = target.doom >= THRESHOLD
        
        if eliminated:
            target.active = 0
            # Check if this is the first elimination
            if not await self.storage.is_roster_locked(self.guild_id):
                await self.storage.lock_roster(self.guild_id)
        
        await self.storage.update_player(target)
        
        # Mark actor as having acted today
        actor.last_action_day = today_key()
        await self.storage.update_player(actor)
        
        # Add/refresh Hex signature
        hex_signature = Signature(
            target_id=target_id,
            signer_id=actor_id,
            guild_id=self.guild_id,
            type="hex",
            expires_at=timestamp_from_hours(SIGNATURE_TTL_HOURS)
        )
        await self.storage.add_signature(hex_signature)
        
        # Update train counts after adding signature
        hex_train_after = await self.get_train_status(target_id, "hex")
        
        # Check if game ended after this elimination
        winner_id = await self.check_game_end()
        
        # Build messages
        veil_text = " (Veil reduced damage)" if veil_active and raw_damage != final_damage else ""
        reflex_text = " Your target triggered Reflex Shield before your Hex resolved!" if reflex_shield_triggered else ""
        
        ephemeral_msg = f"Your Hex deals {final_damage} damage to <@{target_id}>. They are now at {target.doom}/{THRESHOLD} Doom.{veil_text}{reflex_text}"
        
        if eliminated:
            ephemeral_msg += f" <@{target_id}> has been eliminated!"
        
        hex_marks_text = f"{hex_train_after.count} Hex Mark{'s' if hex_train_after.count != 1 else ''}"
        if hex_train_after.count > 0:
            hex_marks_text += f" ({hex_train_after.freshness})"
        
        mend_marks_text = f"{mend_train.count} Mend Mark{'s' if mend_train.count != 1 else ''}"
        if mend_train.count > 0:
            mend_marks_text += f" ({mend_train.freshness})"
        
        public_msg = f"A Hex strikes <@{target_id}> for {final_damage} Doom. <@{target_id}> is now {target.doom}/{THRESHOLD}. {hex_marks_text}. {mend_marks_text}."
        
        if eliminated:
            public_msg += f" <@{target_id}> has been eliminated from the Ritual War!"
            
            if winner_id:
                public_msg += f"\n\n🎉 **RITUAL WAR COMPLETE!** 🎉\n<@{winner_id}> is the last Mage standing and wins the game!"
        
        result = ActionResult(
            True,
            ephemeral_msg,
            public_msg,
            doom_change=final_damage,
            new_doom=target.doom,
            eliminated=eliminated,
            reflex_shield_triggered=reflex_shield_triggered
        )
        result.winner_id = winner_id  # Add winner info to result
        
        return result
    
    async def shield_self(self, user_id: str, bypass_daily_limit: bool = False) -> ActionResult:
        """Execute a Shield action."""
        player = await self.storage.get_player(user_id, self.guild_id)
        if not player or not player.active:
            return ActionResult(False, "You are not in the game.")
        
        can_act, reason = await self.can_act_today(user_id, bypass_daily_limit)
        if not can_act:
            return ActionResult(False, reason)
        
        # Apply Shield effects
        old_doom = player.doom
        player.doom = max(0, player.doom - SHIELD_CLEANSE)
        player.veil_until = timestamp_from_hours(SIGNATURE_TTL_HOURS)
        player.last_action_day = today_key()
        
        await self.storage.update_player(player)
        
        doom_healed = old_doom - player.doom
        
        ephemeral_msg = f"Shield cleanses {doom_healed} Doom and grants you Veil for {SIGNATURE_TTL_HOURS} hours. You are now at {player.doom}/{THRESHOLD} Doom."
        public_msg = f"<@{user_id}> casts Shield and is now at {player.doom}/{THRESHOLD} Doom."
        
        return ActionResult(
            True,
            ephemeral_msg,
            public_msg,
            doom_change=-doom_healed,
            new_doom=player.doom
        )
    
    async def mend_target(self, actor_id: str, target_id: str, bypass_daily_limit: bool = False) -> ActionResult:
        """Execute a Mend action."""
        actor = await self.storage.get_player(actor_id, self.guild_id)
        target = await self.storage.get_player(target_id, self.guild_id)
        
        if not actor or not actor.active:
            return ActionResult(False, "You are not in the game.")
        
        if not target or not target.active:
            return ActionResult(False, "Target is not in the game.")
        
        can_act, reason = await self.can_act_today(actor_id, bypass_daily_limit)
        if not can_act:
            return ActionResult(False, reason)
        
        if await self.storage.has_signature(target_id, actor_id, "mend", self.guild_id):
            return ActionResult(False, "You already have an active Mend signature on this target.")
        
        # Get current mark status
        hex_train = await self.get_train_status(target_id, "hex")
        mend_train = await self.get_train_status(target_id, "mend")
        
        # Calculate healing
        healing = 1 + mend_train.count
        old_doom = target.doom
        target.doom = max(0, target.doom - healing)
        actual_healing = old_doom - target.doom
        
        await self.storage.update_player(target)
        
        # Mark actor as having acted today
        actor.last_action_day = today_key()
        await self.storage.update_player(actor)
        
        # Add/refresh Mend signature
        mend_signature = Signature(
            target_id=target_id,
            signer_id=actor_id,
            guild_id=self.guild_id,
            type="mend",
            expires_at=timestamp_from_hours(SIGNATURE_TTL_HOURS)
        )
        await self.storage.add_signature(mend_signature)
        
        # Update train counts after adding signature
        mend_train_after = await self.get_train_status(target_id, "mend")
        
        ephemeral_msg = f"Your Mend heals {actual_healing} Doom from <@{target_id}>. They are now at {target.doom}/{THRESHOLD} Doom."
        
        hex_marks_text = f"{hex_train.count} Hex Mark{'s' if hex_train.count != 1 else ''}"
        if hex_train.count > 0:
            hex_marks_text += f" ({hex_train.freshness})"
        
        mend_marks_text = f"{mend_train_after.count} Mend Mark{'s' if mend_train_after.count != 1 else ''}"
        if mend_train_after.count > 0:
            mend_marks_text += f" ({mend_train_after.freshness})"
        
        public_msg = f"A Mend heals <@{target_id}> for {actual_healing} Doom. <@{target_id}> is now {target.doom}/{THRESHOLD}. {hex_marks_text}. {mend_marks_text}."
        
        return ActionResult(
            True,
            ephemeral_msg,
            public_msg,
            doom_change=-actual_healing,
            new_doom=target.doom
        )
    
    async def claim_signature(self, claimant_id: str, target_id: str, claim_type: str) -> ActionResult:
        """Make a public claim about contributing to a signature train."""
        claimant = await self.storage.get_player(claimant_id, self.guild_id)
        target = await self.storage.get_player(target_id, self.guild_id)
        
        if not claimant or not claimant.active:
            return ActionResult(False, "You are not in the game.")
        
        if not target or not target.active:
            return ActionResult(False, "Target is not in the game.")
        
        # Get current mark status and claims
        signatures = await self.storage.get_signatures(target_id, claim_type, self.guild_id)
        current_claims = await self.storage.get_claims(target_id, claim_type, self.guild_id)
        
        signature_count = len(signatures)
        claim_count = len(current_claims)
        
        if signature_count == 0:
            return ActionResult(False, f"There is no active {claim_type} train on <@{target_id}>.")
        
        if claim_count >= signature_count:
            return ActionResult(False, f"The {claim_type} train on <@{target_id}> already has the maximum number of claims ({signature_count}).")
        
        # Check if user already claimed
        existing_claim = any(claim.claimant_id == claimant_id for claim in current_claims)
        if existing_claim:
            return ActionResult(False, f"You have already claimed the {claim_type} train on <@{target_id}>.")
        
        # Calculate when this train will expire (when the oldest signature expires)
        train_expires_at = min(sig.expires_at for sig in signatures)
        
        # Add the claim
        from .models import Claim
        claim = Claim(
            target_id=target_id,
            guild_id=self.guild_id,
            type=claim_type,
            claimant_id=claimant_id,
            expires_at=train_expires_at
        )
        await self.storage.add_claim(claim)
        
        action_name = "hexed" if claim_type == "hex" else "mended"
        public_msg = f"<@{claimant_id}> claims to have {action_name} <@{target_id}>."
        
        return ActionResult(
            True,
            f"You have publicly claimed to have {action_name} <@{target_id}>.",
            public_msg
        )
    
    async def unclaim_signature(self, claimant_id: str, target_id: str, claim_type: str) -> ActionResult:
        """Remove a public claim."""
        claimant = await self.storage.get_player(claimant_id, self.guild_id)
        target = await self.storage.get_player(target_id, self.guild_id)
        
        if not claimant or not claimant.active:
            return ActionResult(False, "You are not in the game.")
        
        if not target or not target.active:
            return ActionResult(False, "Target is not in the game.")
        
        current_claims = await self.storage.get_claims(target_id, claim_type, self.guild_id)
        existing_claim = any(claim.claimant_id == claimant_id for claim in current_claims)
        
        if not existing_claim:
            return ActionResult(False, f"You have no claim on the {claim_type} train for <@{target_id}>.")
        
        await self.storage.remove_claim(target_id, claim_type, claimant_id, self.guild_id)
        
        action_name = "hexed" if claim_type == "hex" else "mended"
        return ActionResult(
            True,
            f"You have removed your claim to have {action_name} <@{target_id}>."
        )
    
    async def check_game_end(self) -> str:
        """Check if the game has ended and return winner ID if so."""
        active_players = await self.storage.get_active_players(self.guild_id)
        if len(active_players) == 1:
            return active_players[0].user_id
        return None
    
    async def reset_game(self) -> bool:
        """Reset the game state for a new game."""
        try:
            # Clear all game data
            await self.storage.clear_all_game_data(self.guild_id)
            return True
        except Exception as e:
            return False