#!/usr/bin/env python3
"""
Media Search Bot - Telegram bot for indexing and searching media files
Optimized for Render hosting with built-in keep-alive
"""

import asyncio
import logging
import os
import sys
from threading import Thread
from pyrogram import Client, __version__
from pyrogram.raw.all import layer
from config import Config
from database import Database
from storage import Storage

# Logging setup (No logging.conf required)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Optional keep_alive import
try:
    from keep_alive import keep_alive
    HAS_KEEP_ALIVE = True
except ImportError:
    HAS_KEEP_ALIVE = False
    logger.warning("keep_alive.py not found. Bot may sleep on free hosting without it.")

class MediaSearchBot:
    def __init__(self):
        self.config = Config()
        self.storage = Storage()
        self.database = Database()

        # Ensure required environment variables are set
        required_env = ["API_ID", "API_HASH", "BOT_TOKEN"]
        for var in required_env:
            if not getattr(self.config, var, None):
                logger.error(f"Missing required config: {var}")
                sys.exit(1)

        # Initialize Pyrogram client
        self.app = Client(
            "MediaSearchBot",
            api_id=self.config.API_ID,
            api_hash=self.config.API_HASH,
            bot_token=self.config.BOT_TOKEN,
            workers=50,
            sleep_threshold=5,
            max_concurrent_transmissions=10
        )

    async def start(self):
        """Start the bot"""
        try:
            logger.info("Starting Media Search Bot...")

            # Start keep-alive thread if available
            if HAS_KEEP_ALIVE:
                Thread(target=keep_alive, daemon=True).start()

            # Start bot
            await self.app.start()

            # Initialize database
            await self.database.initialize()

            # Load storage data
            await self.storage.load_data()

            # Register handlers
            from handlers import MediaSearchHandlers
            self.handlers = MediaSearchHandlers(self.app)
            self.handlers.storage = self.storage
            self.handlers.config = self.config
            self.handlers.database = self.database

            # Get bot info
            me = await self.app.get_me()
            self.username = f"@{me.username}"

            logger.info(
                f"🚀 {me.first_name} started successfully!\n"
                f"📊 Pyrogram v{__version__} (Layer {layer})\n"
                f"🔗 Username: {me.username}\n"
                f"💾 Database: {self.config.DATABASE_NAME}\n"
                f"👥 Admins: {len(self.config.ADMINS)}\n"
                f"📺 Channels: {len(self.config.CHANNELS)}"
            )

            # Update bot stats
            if hasattr(self.storage, "update_bot_stats"):
                await self.storage.update_bot_stats({
                    "bot_started": True,
                    "username": me.username,
                    "start_time": asyncio.get_event_loop().time()
                })

            # Keep running
            await asyncio.Event().wait()

        except Exception as e:
            logger.exception("❌ Failed to start bot")
            sys.exit(1)

    async def stop(self):
        """Stop the bot gracefully"""
        try:
            logger.info("🛑 Stopping Media Search Bot...")
            if hasattr(self.storage, "save_data"):
                if asyncio.iscoroutinefunction(self.storage.save_data):
                    await self.storage.save_data()
                else:
                    self.storage.save_data()
            await self.app.stop()
            logger.info("✅ Bot stopped successfully")
        except Exception as e:
            logger.exception("❌ Error during bot shutdown")

async def main():
    bot = MediaSearchBot()
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("🔄 Received shutdown signal")
    except Exception:
        logger.exception("💥 Unexpected error")
    finally:
        await bot.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Bot shutdown completed")
    except Exception:
        logger.exception("💥 Fatal error")
        sys.exit(1)
