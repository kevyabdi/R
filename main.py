#!/usr/bin/env python3
"""
Media Search Bot - Telegram bot for indexing and searching media files
Optimized for Render hosting with Flask keep-alive server
"""

import asyncio
import logging
import logging.config
import os
import sys
from threading import Thread
from pyrogram.client import Client
from pyrogram import __version__
from pyrogram.raw.all import layer
from config import Config
from database import Database
from storage import Storage
from keep_alive import keep_alive
from handlers import MediaSearchHandlers

# Configure logging
logging.config.fileConfig('logging.conf', disable_existing_loggers=False)
logger = logging.getLogger(__name__)

class MediaSearchBot:
    def __init__(self):
        self.config = Config()
        self.storage = Storage()
        self.database = Database()
        
        # Initialize Pyrogram client with better session handling
        self.app = Client(
            "MediaSearchBot",
            api_id=self.config.API_ID,
            api_hash=self.config.API_HASH,
            bot_token=self.config.BOT_TOKEN,
            workers=50,
            plugins={"root": "Plugins"},
            sleep_threshold=5,
            max_concurrent_transmissions=10,
            no_updates=False
        )

    async def start(self):
        """Start the bot and initialize components"""
        try:
            logger.info("Starting Media Search Bot...")
            
            # Start keep-alive server
            keep_alive()
            
            # Clean up any existing session files on startup
            session_files = [f for f in os.listdir('.') if f.endswith('.session') or f.endswith('.session-journal')]
            for session_file in session_files:
                try:
                    os.remove(session_file)
                    logger.info(f"🗑️ Removed old session file: {session_file}")
                except Exception as e:
                    logger.warning(f"Could not remove {session_file}: {e}")
            
            # Start Pyrogram client
            await self.app.start()
            
            # Initialize database
            await self.database.initialize()
            
            # Load storage data
            await self.storage.load_data()
            
            # Register handlers
            self.handlers = MediaSearchHandlers(self.app)
            self.handlers.storage = self.storage
            self.handlers.config = self.config
            self.handlers.database = self.database
            
            # Get bot information
            me = await self.app.get_me()
            self.username = f'@{me.username}'
            
            logger.info(
                f"🚀 {me.first_name} started successfully!\n"
                f"📊 Pyrogram v{__version__} (Layer {layer})\n"
                f"🔗 Username: {me.username}\n"
                f"💾 Database: {self.config.DATABASE_NAME}\n"
                f"👥 Admins: {len(self.config.ADMINS)}\n"
                f"📺 Channels: {len(self.config.CHANNELS)}"
            )
            
            # Update bot stats
            await self.storage.update_bot_stats({
                'bot_started': True,
                'username': me.username,
                'start_time': asyncio.get_event_loop().time()
            })
            
            # Keep the bot running
            await asyncio.Event().wait()
            
        except Exception as e:
            logger.error(f"❌ Failed to start bot: {e}")
            sys.exit(1)

    async def stop(self):
        """Stop the bot gracefully"""
        try:
            logger.info("🛑 Stopping Media Search Bot...")
            await self.storage.save_data()
            
            # Check if client is still running before stopping
            if hasattr(self.app, 'is_initialized') and self.app.is_initialized:
                await self.app.stop()
            elif not getattr(self.app, 'is_terminated', False):
                await self.app.stop()
            
            logger.info("✅ Bot stopped successfully")
        except Exception as e:
            logger.error(f"❌ Error during bot shutdown: {e}")

async def main():
    """Main function to run the bot"""
    bot = MediaSearchBot()
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("🔄 Received shutdown signal")
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
    finally:
        await bot.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Bot shutdown completed")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        sys.exit(1)
