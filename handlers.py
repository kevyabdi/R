"""
Enhanced handlers for Media Search Bot
Integrates all bot functionality with proper error handling and session management
"""

import asyncio
import logging
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import (
    Message, InlineQuery, InlineQueryResultDocument,
    InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery
)
from pyrogram.errors import FloodWait, UserIsBlocked, ChatAdminRequired, ChannelPrivate

from config import Config
from storage import Storage
from database import Database
from utils.helpers import (
    format_file_size, format_duration, extract_search_terms,
    get_file_emoji, validate_user_id, query_rate_limiter
)

logger = logging.getLogger(__name__)


class MediaSearchHandlers:
    def __init__(self, app: Client):
        self.app = app
        self.config = Config()
        self.storage = Storage()
        self.database = Database()

        self._register_handlers()

    def _register_handlers(self):
        """Register all bot handlers"""

        # Commands
        self.app.add_handler(filters.command("start") & filters.private)(self.start_command)
        self.app.add_handler(filters.command("help") & filters.private)(self.help_command)
        self.app.add_handler(filters.command("stats") & filters.private)(self.stats_command)

        # Inline search
        @self.app.on_inline_query()
        async def inline_search(client, inline_query: InlineQuery):
            query = inline_query.query.strip()
            if not query:
                await inline_query.answer([], switch_pm_text="Type to search files", switch_pm_parameter="start")
                return

            results = await self.database.search_files(query)
            answers = []
            for file in results:
                answers.append(
                    InlineQueryResultDocument(
                        title=file['file_name'],
                        document_url=file['file_url'],
                        mime_type="application/octet-stream",
                        caption=f"{get_file_emoji(file['mime_type'])} {file['file_name']}\n"
                                f"Size: {format_file_size(file['file_size'])}\n"
                                f"Duration: {format_duration(file['duration'])}",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Download", url=file['file_url'])]])
                    )
                )

            await inline_query.answer(answers, cache_time=1)

    async def start_command(self, client: Client, message: Message):
        await message.reply_text(
            f"Hello {message.from_user.first_name}, welcome to Media Search Bot! 🔍",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Help", callback_data="help")]])
        )

    async def help_command(self, client: Client, message: Message):
        await message.reply_text(
            "Send me a keyword and I will find matching media files.\n"
            "Or use me inline in any chat: `@YourBotName keyword`"
        )

    async def stats_command(self, client: Client, message: Message):
        stats = await self.database.get_stats()
        await message.reply_text(
            f"📊 **Bot Stats**\n"
            f"• Total Files: {stats.get('total_files', 0)}\n"
            f"• Total Users: {stats.get('total_users', 0)}\n"
            f"• Total Searches: {stats.get('total_searches', 0)}"
        )


# ✅ Usage example
# from pyrogram import Client
# app = Client("MediaSearchBot", api_id=..., api_hash=..., bot_token=...)
# MediaSearchHandlers(app)
# app.run()
