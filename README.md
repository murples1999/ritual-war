# Ritual War Discord Bot

A multi-server Discord bot for running the "Ritual War" game - a strategic social game where players cast spells to be the last mage standing.

## 🎮 Game Overview

Ritual War is a daily-action strategy game where players:
- **Join** the game as mages
- **Cast one spell per day** (Hex to attack, Shield to protect, Mend to heal)
- **Make public claims** about their actions to influence others
- **Survive** until they're the last mage standing to win

### Core Mechanics
- **Doom System**: Players start with 0 doom and are eliminated at 12+ doom
- **Daily Actions**: One action per day based on Pacific Time
- **Signature System**: Multiple players targeting the same person increases spell effectiveness
- **Social Layer**: Public claims can be true or false to create political gameplay

## 🌟 Features

- **Multi-Server Support**: Each Discord server has completely isolated game states
- **Flexible Channel Configuration**: Admins can set which channel receives public messages
- **Daily Notifications**: Automated reminders for active players
- **Comprehensive Logging**: Full audit trail of all game actions
- **Robust Error Handling**: Automatic recovery from common issues

## 🛠️ Setup

### Prerequisites
- Python 3.11+
- Discord Bot Token
- Discord Application with appropriate permissions

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/murples1999/ritual-war.git
   cd ritual-war
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your bot token
   ```

5. **Run the bot**:
   ```bash
   python bot.py
   ```

### Environment Variables

Create a `.env` file with:

```env
DISCORD_BOT_TOKEN=your_bot_token_here
BOT_OWNER_ID=your_discord_user_id  # Optional, for admin commands
```

### Discord Bot Permissions

Required permissions:
- `Send Messages`
- `Use Slash Commands`  
- `Embed Links`
- `Read Message History`
- `View Channels`

### Bot Invite URL
Replace `YOUR_BOT_CLIENT_ID` with your bot's client ID:
```
https://discord.com/api/oauth2/authorize?client_id=YOUR_BOT_CLIENT_ID&permissions=277025524800&scope=bot%20applications.commands
```

## 📋 Commands

### Player Commands
- `/join` - Join the Ritual War game
- `/leave` - Leave the game  
- `/hex <target>` - Cast Hex spell on target player
- `/shield` - Cast Shield spell on yourself
- `/mend <target>` - Cast Mend spell on target player
- `/inspect [player]` - Check a player's status (defaults to self)
- `/leaderboard` - View current game state and all players
- `/claimhex <target>` - Publicly claim you hexed a player
- `/claimmend <target>` - Publicly claim you mended a player
- `/unclaim <target> <action>` - Remove a public claim

### Admin Commands  
- `/admin_setchannel <channel>` - Set channel for public messages (Admin only)
- `/admin_reset_game` - Reset the entire game state (Bot owner only)
- `/admin_force_winner <player>` - Manually declare a winner (Bot owner only) 
- `/admin_advance_day` - Reset daily action limits for testing (Bot owner only)

## 🏗️ Architecture

```
ritual-war/
├── bot.py                 # Main bot entry point
├── error_handler.py       # Global error handling
├── requirements.txt       # Python dependencies
├── .env.example          # Environment template
├── game/
│   ├── commands.py        # Player slash commands
│   ├── admin_commands.py  # Admin-only commands
│   ├── logic.py          # Core game mechanics
│   ├── storage.py        # Database operations  
│   ├── models.py         # Data structures
│   ├── view.py           # Discord message formatting
│   ├── notifications.py  # Channel management
│   ├── scheduler.py      # Daily notification system
│   ├── config.py         # Game configuration
│   └── timeutils.py      # Timezone utilities
```

## 🗄️ Database

Uses SQLite with guild-based data isolation:
- **players**: Player information per server
- **signatures**: Active spell effects with expiration  
- **claims**: Public claims made by players
- **game_state**: Per-server configuration

## 🔧 Configuration

Game settings in `game/config.py`:
- `THRESHOLD = 12` - Doom points for elimination
- `SHIELD_CLEANSE = 2` - Doom removed by Shield  
- `SIGNATURE_TTL_HOURS = 24` - How long spell effects last
- `VEIL_REDUCTION = 0.5` - Shield damage reduction (50%)

## 🎯 Game Rules

### Victory Condition
Be the last active player remaining.

### Spells
- **Hex**: Deal damage based on number of hexers targeting the same player
- **Shield**: Reduce your doom by 2 and gain 50% damage reduction for 24 hours
- **Mend**: Heal damage based on number of menders targeting the same player

### Social Elements
- **Claims**: Publicly announce your actions (can be true or false)
- **Signatures**: Spell effects stack when multiple players target the same person
- **Daily Limits**: One action per player per day

## 📊 Logging

The bot logs all game actions, errors, and system events to `ritual_war.log` for debugging and monitoring.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License.