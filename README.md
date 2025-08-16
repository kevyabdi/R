# Media Search Bot 🔍

A powerful Telegram bot for indexing and searching media files across multiple channels using advanced inline queries.

## Features ✨

- **📁 Multi-format Support**: Documents, Videos, Audio, Photos, Animations
- **🔍 Smart Search**: Filename and caption-based search with text indexing
- **⚡ Inline Queries**: Fast search directly in any chat using `@botusername search_term`
- **🛡️ Advanced Security**: Multi-level authorization and ban system
- **📊 Analytics**: Comprehensive statistics and user tracking
- **🔄 Auto-indexing**: Real-time media indexing from configured channels
- **👥 Admin Controls**: Full bot management with admin commands

## Tech Stack 🛠️

- **Framework**: [Pyrogram](https://docs.pyrogram.org/) (Async Telegram Bot API)
- **Database**: MongoDB with text indexing
- **Storage**: JSON-based user data persistence
- **Hosting**: Optimized for Replit with Flask keep-alive server
- **Logging**: Comprehensive logging system

## Quick Start 🚀

### 1. Clone & Setup

```bash
git clone https://github.com/yourusername/media-search-bot.git
cd media-search-bot
```

### 2. Environment Variables

Set up these required environment variables in Replit Secrets or `.env`:

```bash
# Telegram API (Get from https://my.telegram.org)
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token

# MongoDB Database
DATABASE_URI=mongodb+srv://username:password@cluster.mongodb.net/
DATABASE_NAME=your_database_name
COLLECTION_NAME=telegram_files

# Bot Configuration
ADMINS=123456789,987654321  # Admin user IDs (comma-separated)
CHANNELS=-1001234567890,-1009876543210  # Channel IDs to index
AUTH_CHANNEL=@your_channel  # Optional: Required subscription channel
AUTH_USERS=  # Optional: Specific authorized users only

# Optional Settings
CACHE_TIME=300  # Inline query cache time in seconds
USE_CAPTION_FILTER=True  # Search in captions
```

### 3. Run the Bot

```bash
python main.py
```

## Bot Commands 📋

### User Commands
- `/start` - Welcome message and bot introduction
- `/help` - Detailed usage guide and tips

### Admin Commands
- `/stats` - Comprehensive bot statistics
- `/ban <user_id>` - Ban a user from the bot
- `/unban <user_id>` - Unban a user
- `/broadcast <message>` - Send message to all users
- `/index [channel_id] [limit]` - Force re-index channels
- `/delete <file_id>` - Remove file from database
- `/total` - Show total indexed files count
- `/channel` - Channel information and status
- `/logger` - Download bot log file

## Usage Examples 💡

### Basic Search
```
@yourbotusername python tutorial
```

### File Type Filtering
```
@yourbotusername movie | video
@yourbotusername music | audio
@yourbotusername ebook | document
@yourbotusername wallpaper | photo
```

### Advanced Searches
```
@yourbotusername "exact phrase search"
@yourbotusername programming python | document
```

## Configuration 🔧

### Channel Setup
1. Add your bot to channels you want to index
2. Make sure the bot has permission to read messages
3. Add channel IDs to `CHANNELS` environment variable

### Database Indexing
The bot automatically creates text indexes for:
- File names
- File captions
- Channel titles

### Authentication Levels
1. **Public**: Anyone can use (default)
2. **Auth Users**: Only specific user IDs
3. **Channel Subscription**: Must join a channel first
4. **Admin**: Full bot management access

## Architecture 🏗️

```
├── main.py              # Bot entry point and initialization
├── config.py            # Configuration management
├── handlers.py          # Enhanced command and query handlers
├── database.py          # MongoDB operations and indexing
├── storage.py           # JSON-based data persistence
├── keep_alive.py        # Flask server for hosting platforms
├── Plugins/            
│   ├── commands.py      # Command handlers
│   ├── inline_query.py  # Inline query processing
│   └── channel_post.py  # Auto-indexing handlers
└── Utils/
    ├── helpers.py       # Utility functions
    └── filters.py       # Custom Pyrogram filters
```

## Features in Detail 📖

### Smart Search Algorithm
- Full-text search across filenames and captions
- Support for partial matches and fuzzy searching
- File type filtering with intelligent categorization
- Results ranked by relevance and file popularity

### Security Features
- Rate limiting to prevent spam
- Multi-level user authorization
- Session management with automatic recovery
- Comprehensive error handling and logging

### Admin Dashboard
- Real-time statistics and analytics
- User management (ban/unban system)
- Channel monitoring and file counts
- Broadcast messaging to all users
- Manual indexing controls

### Performance Optimizations
- Asynchronous processing for all operations
- Database connection pooling
- Intelligent caching for frequently accessed data
- Memory-efficient file processing

## Deployment 🌐

### Replit (Recommended)
1. Fork this repository to Replit
2. Set up environment variables in Secrets
3. Click Run - the bot will start automatically
4. Use the provided keep-alive server for 24/7 uptime

### Manual Deployment
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export API_ID=your_api_id
export API_HASH=your_api_hash
# ... other variables

# Run the bot
python main.py
```

## Monitoring & Logs 📊

### Built-in Analytics
- User interaction tracking
- Search query analytics
- File sharing statistics
- Channel activity monitoring

### Logging System
- Comprehensive error tracking
- Performance monitoring
- User activity logs
- Admin action auditing

## Contributing 🤝

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License 📄

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support 💬

- Create an issue for bug reports
- Join our Telegram support group: [@yoursupportgroup](https://t.me/yoursupportgroup)
- Documentation: [Wiki](https://github.com/yourusername/media-search-bot/wiki)

## Acknowledgments 👏

- [Pyrogram](https://github.com/pyrogram/pyrogram) - Modern Telegram Bot API framework
- [MongoDB](https://www.mongodb.com/) - Document database for file indexing
- [Replit](https://replit.com/) - Cloud development platform

---

**Made with ❤️ for the Telegram community**

[![Deploy on Replit](https://replit.com/badge/github/yourusername/media-search-bot)](https://replit.com/github/yourusername/media-search-bot)
