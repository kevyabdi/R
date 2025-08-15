"""
Configuration management for Media Search Bot
Handles environment variables and bot settings
"""

import os
import logging

logger = logging.getLogger(__name__)

class Config:
    def __init__(self):
        # Required Telegram API credentials
        self.API_ID = int(os.getenv("API_ID", "0"))
        self.API_HASH = os.getenv("API_HASH", "")
        self.BOT_TOKEN = os.getenv("BOT_TOKEN", "")
        
        # Database configuration
        self.DATABASE_URI = os.getenv("DATABASE_URI", "")
        self.DATABASE_NAME = os.getenv("DATABASE_NAME", "MediaSearchBot")
        self.COLLECTION_NAME = os.getenv("COLLECTION_NAME", "telegram_files")
        
        # Bot settings
        self.CACHE_TIME = int(os.getenv("CACHE_TIME", "300"))
        self.USE_CAPTION_FILTER = os.getenv("USE_CAPTION_FILTER", "True").lower() == "true"
        
        # Admin and channel configuration
        self.ADMINS = self._parse_list(os.getenv("ADMINS", ""))
        self.CHANNELS = self._parse_list(os.getenv("CHANNELS", ""))
        self.AUTH_USERS = self._parse_list(os.getenv("AUTH_USERS", ""))
        self.AUTH_CHANNEL = os.getenv("AUTH_CHANNEL", "")
        
        # Messages
        self.START_MSG = os.getenv("START_MSG", self._default_start_message())
        self.INVITE_MSG = os.getenv("INVITE_MSG", "Please join the required channel to use this bot")
        self.SHARE_BUTTON_TEXT = os.getenv("SHARE_BUTTON_TEXT", "Checkout {username} for searching files")
        
        # Validate required settings
        self._validate_config()
    
    def _parse_list(self, value):
        """Parse comma-separated string into list of integers/strings"""
        if not value:
            return []
        
        items = []
        for item in value.split(','):
            item = item.strip()
            if item:
                try:
                    # Try to convert to int (for user IDs/channel IDs)
                    num = int(item)
                    # For channel IDs, ensure they have proper -100 prefix if they're large positive numbers
                    if num > 0 and len(str(num)) > 10:  # Likely a channel ID without -100 prefix
                        num = -int(f"100{num}")
                    items.append(num)
                except ValueError:
                    # Keep as string (for usernames/channel names)
                    items.append(item)
        return items
    
    def _default_start_message(self):
        return """**🔍 Welcome to Media Search Bot!**

I can help you search for files across indexed channels. Here's how to use me:

🔎 **Inline Search**: Type `@{username} <search term>` in any chat
📁 **File Types**: Documents, Videos, Audio, Photos
🏷️ **Search Tips**: Use keywords from filename or caption

**Admin Commands** (Admins only):
• `/stats` - View bot statistics
• `/ban <user_id>` - Ban a user
• `/unban <user_id>` - Unban a user
• `/broadcast <message>` - Send message to all users
• `/index` - Force re-index channels
• `/total` - Show total indexed files

**Made with ❤️ using Pyrogram**"""
    
    def _validate_config(self):
        """Validate essential configuration"""
        errors = []
        
        if not self.API_ID or self.API_ID == 0:
            errors.append("API_ID is required")
        
        if not self.API_HASH:
            errors.append("API_HASH is required")
        
        if not self.BOT_TOKEN:
            errors.append("BOT_TOKEN is required")
        
        if not self.DATABASE_URI:
            errors.append("DATABASE_URI is required")
        
        if not self.ADMINS:
            errors.append("At least one ADMIN is required")
        
        if errors:
            error_msg = "Configuration errors:\n" + "\n".join(f"- {error}" for error in errors)
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info("✅ Configuration validated successfully")
    
    def is_admin(self, user_id):
        """Check if user is admin"""
        return user_id in self.ADMINS
    
    def is_auth_user(self, user_id):
        """Check if user is authorized (if AUTH_USERS is set)"""
        if not self.AUTH_USERS:
            return True  # No restriction if AUTH_USERS is empty
        return user_id in self.AUTH_USERS
