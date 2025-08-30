# Ritual War Discord Bot

A multi-server Discord bot for running the "Ritual War" game - a social deduction game where players cast spells on each other to be the last mage standing.

## 🎮 Game Overview

Ritual War is a strategic social game where players:
- **Join** the game as mages
- **Cast spells** on other players (Hex to deal damage, Shield to protect, Mend to heal)
- **Make claims** about their actions to influence others
- **Survive** until they're the last mage standing to win

### Game Mechanics
- **Doom Points**: Players start with 0 doom and are eliminated at 12+ doom
- **Daily Actions**: Each player can perform one action per day
- **Spells**:
  - 🔥 **Hex**: Deal 2-4 doom damage to a target
  - 🛡️ **Shield**: Protect yourself, reducing next damage by 50% and cleansing 2 doom
  - 💚 **Mend**: Remove 2-4 doom from a target
- **Claims**: Publicly announce your actions to influence the game
- **Time Zones**: Actions refresh based on Pacific Time zones (Fresh/Warm/Cooling periods)

## 🌟 Features

- **Multi-Server Support**: Each Discord server has completely isolated game states
- **Flexible Channel Configuration**: Admins can set which channel receives public game messages
- **Daily Notifications**: Automated reminders sent to all active players
- **XP Integration**: Winners receive XP rewards (requires separate XP bot)
- **Comprehensive Logging**: Full audit trail of all game actions
- **Error Handling**: Robust error handling with automatic recovery

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
   # Edit .env with your bot token and configuration
   ```

5. **Run the bot**:
   ```bash
   python bot.py
   ```

### Environment Variables

Create a `.env` file with the following variables:

```env
# Required
DISCORD_BOT_TOKEN=your_bot_token_here

# Optional
BOT_OWNER_ID=your_discord_user_id
HEAD_DM_ID=discord_user_id_for_xp_notifications
```

### Discord Bot Permissions

The bot requires the following permissions:
- `Send Messages`
- `Use Slash Commands`
- `Embed Links`
- `Read Message History`
- `View Channels`

### Invite URL
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
- `/inspect [player]` - Check a player's status (or your own)
- `/leaderboard` - View current game state and all players
- `/claimhex <target>` - Publicly claim you hexed a player
- `/claimmend <target>` - Publicly claim you mended a player
- `/unclaim <target> <action>` - Remove a public claim

### Admin Commands
- `/admin_setchannel <channel>` - Set the channel for public game messages (Admin only)
- `/admin_reset_game` - Reset the entire game state (Bot owner only)
- `/admin_force_winner <player>` - Manually declare a winner (Bot owner only)
- `/admin_advance_day` - Reset daily action limits for testing (Bot owner only)

## 🏗️ Architecture

```
ritual-war/
├── bot.py                 # Main bot entry point
├── error_handler.py       # Global error handling
├── requirements.txt       # Python dependencies
├── game/
│   ├── __init__.py
│   ├── commands.py        # Slash command definitions
│   ├── admin_commands.py  # Admin-only commands
│   ├── logic.py          # Core game logic
│   ├── storage.py        # Database operations
│   ├── models.py         # Data models
│   ├── view.py           # Message formatting
│   ├── notifications.py  # Channel management & notifications
│   ├── scheduler.py      # Daily notification scheduler
│   ├── config.py         # Game configuration
│   └── timeutils.py      # Time zone utilities
└── .env                  # Environment configuration (not in repo)
```

## 🗄️ Database Schema

The bot uses SQLite with the following tables:
- **players**: Player information (user_id, guild_id, doom, veil_until, etc.)
- **signatures**: Public claims made by players
- **game_state**: Per-guild game configuration and state

All data is isolated by `guild_id` for multi-server support.

## 🔧 Configuration

### Game Settings (config.py)
- `THRESHOLD`: Doom points needed for elimination (default: 12)
- `SHIELD_CLEANSE`: Doom removed by Shield spell (default: 2)
- `SIGNATURE_TTL_HOURS`: How long claims last (default: 24 hours)
- `VEIL_REDUCTION`: Shield damage reduction (default: 50%)
- `XP_REWARD_AMOUNT`: XP awarded to winners (default: 100)

### Time Zones
The game uses Pacific Time with three periods:
- **Fresh** (12 AM - 6 AM): Optimal action time
- **Warm** (6 AM - 6 PM): Standard action time  
- **Cooling** (6 PM - 12 AM): Action time with warnings

## 🚀 Deployment

### Systemd Service (Linux)
```ini
[Unit]
Description=Ritual War Discord Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/ritual-war
ExecStart=/path/to/ritual-war/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Docker (Optional)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "bot.py"]
```

## 📊 Logging

The bot provides comprehensive logging:
- Game actions and results
- Command usage and errors
- Daily notification delivery
- Database operations
- Discord API interactions

Logs are written to `ritual_war.log` with rotation.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support, create an issue on GitHub or contact the bot administrator.

## 🎯 Roadmap

- [ ] Web dashboard for game management
- [ ] Additional spell types
- [ ] Tournament mode
- [ ] Player statistics and achievements
- [ ] Custom game rule configurations per server

---

*Made with ❤️ for D&D communities*