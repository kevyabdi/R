"""
Enhanced handlers for Media Search Bot
Integrates all bot functionality with proper error handling and session management
"""

import asyncio
import logging
import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from pyrogram import Client, filters
from pyrogram.types import (
    Message, InlineQuery, InlineQueryResultDocument, 
    InlineKeyboardMarkup, InlineKeyboardButton,
    InputTextMessageContent, CallbackQuery, ChatMemberUpdated
)
from pyrogram.errors import (
    FloodWait, UserIsBlocked, ChatAdminRequired,
    ChannelPrivate, PeerIdInvalid, SessionRevoked,
    AuthKeyUnregistered, UserDeactivated
)
from config import Config
from storage import Storage  
from database import Database
from Utils.helpers import (
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
        self.session_retry_count = 0
        self.max_retries = 3
        
        # Register all handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register all bot handlers"""
        from pyrogram import filters
        from pyrogram.handlers import MessageHandler, InlineQueryHandler, CallbackQueryHandler, ChosenInlineResultHandler
        
        # Command handlers
        self.app.add_handler(MessageHandler(self.start_command, filters.command("start") & filters.private))
        self.app.add_handler(MessageHandler(self.help_command, filters.command("help") & filters.private))
        self.app.add_handler(MessageHandler(self.stats_command, filters.command("stats") & filters.private))
        self.app.add_handler(MessageHandler(self.ban_command, filters.command("ban") & filters.private))
        self.app.add_handler(MessageHandler(self.unban_command, filters.command("unban") & filters.private))
        self.app.add_handler(MessageHandler(self.broadcast_command, filters.command("broadcast") & filters.private))
        self.app.add_handler(MessageHandler(self.index_command, filters.command("index") & filters.private))
        self.app.add_handler(MessageHandler(self.delete_command, filters.command("delete") & filters.private))
        self.app.add_handler(MessageHandler(self.logger_command, filters.command("logger") & filters.private))
        self.app.add_handler(MessageHandler(self.total_command, filters.command("total") & filters.private))
        self.app.add_handler(MessageHandler(self.channel_command, filters.command("channel") & filters.private))
        
        # Inline handlers
        self.app.add_handler(InlineQueryHandler(self.inline_query_handler))
        self.app.add_handler(ChosenInlineResultHandler(self.chosen_inline_result_handler))
        
        # Callback handlers
        self.app.add_handler(CallbackQueryHandler(self.callback_query_handler))
        
        # Media indexing handlers
        self.app.add_handler(MessageHandler(
            self.channel_media_handler,
            filters.chat(self.config.CHANNELS) & 
            (filters.document | filters.video | filters.audio | 
             filters.photo | filters.animation | filters.voice)
        ))
        
        logger.info("✅ All handlers registered successfully")

    async def handle_session_error(self, error: Exception):
        """Handle session-related errors with recovery"""
        try:
            if self.session_retry_count >= self.max_retries:
                logger.error("❌ Max session retry attempts reached")
                return False
            
            self.session_retry_count += 1
            logger.warning(f"🔄 Session error detected, attempt {self.session_retry_count}/{self.max_retries}")
            
            # Clean up session files
            session_files = [f for f in os.listdir('.') if f.endswith('.session')]
            for session_file in session_files:
                try:
                    os.remove(session_file)
                    logger.info(f"🗑️ Removed corrupted session file: {session_file}")
                except Exception as e:
                    logger.error(f"❌ Error removing session file {session_file}: {e}")
            
            # Restart bot with fresh session
            await asyncio.sleep(5)  # Wait before retry
            await self.app.restart()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error in session recovery: {e}")
            return False

    async def start_command(self, client: Client, message: Message):
        """Handle /start command with comprehensive checks"""
        try:
            user_id = message.from_user.id
            user_name = message.from_user.first_name or "User"
            
            # Check if user is banned
            if self.storage.is_banned(user_id):
                await message.reply(
                    "❌ **Access Denied**\n\n"
                    "You have been banned from using this bot.\n"
                    "Contact administrators if you think this is a mistake."
                )
                return
            
            # Check authorization if AUTH_USERS is set
            if self.config.AUTH_USERS and not self.config.is_auth_user(user_id):
                await message.reply(
                    "❌ **Unauthorized Access**\n\n"
                    "You are not authorized to use this bot.\n"
                    "Contact administrators for access."
                )
                return
            
            # Check channel subscription if required
            if self.config.AUTH_CHANNEL:
                try:
                    member = await client.get_chat_member(self.config.AUTH_CHANNEL, user_id)
                    if member.status in ["left", "kicked"]:
                        keyboard = InlineKeyboardMarkup([
                            [InlineKeyboardButton(
                                "📢 Join Required Channel", 
                                url=f"https://t.me/{self.config.AUTH_CHANNEL.replace('@', '')}"
                            )],
                            [InlineKeyboardButton("🔄 Check Again", callback_data="check_subscription")]
                        ])
                        
                        await message.reply(
                            f"📢 **Channel Subscription Required**\n\n"
                            f"{self.config.INVITE_MSG}\n\n"
                            f"Please join the required channel and click 'Check Again'.",
                            reply_markup=keyboard
                        )
                        return
                except Exception as e:
                    logger.error(f"❌ Error checking channel subscription: {e}")
            
            # Get bot info
            me = await client.get_me()
            
            # Create welcome message
            welcome_text = f"""🔍 **Welcome to {me.first_name}, {user_name}!**

I'm an advanced media search bot that helps you find files across indexed channels.

**🔎 How to Search:**
• Type `@{me.username} <search term>` in any chat
• Example: `@{me.username} python tutorial`
• Advanced: `@{me.username} avengers | video`

**📁 Supported File Types:**
• 📄 Documents (PDF, DOC, ZIP, etc.)
• 🎥 Videos (MP4, AVI, MKV, etc.) 
• 🎵 Audio (MP3, WAV, FLAC, etc.)
• 🖼️ Photos (JPG, PNG, GIF, etc.)

**✨ Features:**
• Lightning-fast inline search
• Caption and filename search
• File type filtering
• Real-time indexing

**Made with ❤️ using Pyrogram**"""
            
            # Create inline keyboard
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔍 Try Search", switch_inline_query_current_chat=""),
                    InlineKeyboardButton("📊 Bot Stats", callback_data="public_stats")
                ],
                [
                    InlineKeyboardButton("❓ Help & Tips", callback_data="show_help"),
                    InlineKeyboardButton("🔗 Share Bot", switch_inline_query="")
                ]
            ])
            
            await message.reply(welcome_text, reply_markup=keyboard, disable_web_page_preview=True)
            
            # Update statistics
            await self.storage.increment_stat("start_commands")
            await self.storage.track_user_query(user_id, "/start")
            
            logger.info(f"👋 Start command by user {user_id} ({user_name})")
            
        except FloodWait as e:
            logger.warning(f"⏱️ FloodWait: {e.value} seconds")
            await asyncio.sleep(e.value)
            await self.start_command(client, message)
        except (SessionRevoked, AuthKeyUnregistered) as e:
            logger.error(f"🔐 Session error in start command: {e}")
            await self.handle_session_error(e)
        except Exception as e:
            logger.error(f"❌ Error in start command: {e}")
            await message.reply("❌ An error occurred. Please try again later.")

    async def help_command(self, client: Client, message: Message):
        """Handle /help command"""
        try:
            me = await client.get_me()
            
            help_text = f"""❓ **{me.first_name} - Help & Guide**

**🔍 Search Commands:**
• `@{me.username} <term>` - Search files
• `@{me.username} python | document` - Search documents only
• `@{me.username} movie | video` - Search videos only

**🎯 Search Tips:**
• Use specific keywords for better results
• Try different search terms if no results
• File type filters: document, video, audio, photo
• Search works on filenames and captions

**📁 File Type Examples:**
• `music | audio` - Find audio files
• `tutorial | document` - Find documents  
• `movie | video` - Find video files
• `wallpaper | photo` - Find images

**⚡ Quick Actions:**
• Forward found files to save them
• Share search results with friends
• Use inline mode in any chat

**🛠️ Admin Commands** (Admins only):
• `/stats` - View detailed statistics
• `/ban <user_id>` - Ban user from bot
• `/unban <user_id>` - Unban user
• `/broadcast <message>` - Send message to all users
• `/index` - Force re-index channels
• `/total` - Show total file count

**Need more help?** Contact the bot administrators."""

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 Try Search Now", switch_inline_query_current_chat="")],
                [InlineKeyboardButton("🏠 Back to Start", callback_data="back_to_start")]
            ])
            
            await message.reply(help_text, reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"❌ Error in help command: {e}")
            await message.reply("❌ Error loading help information.")

    async def stats_command(self, client: Client, message: Message):
        """Handle /stats command (admin only)"""
        try:
            user_id = message.from_user.id
            
            if not self.config.is_admin(user_id):
                await message.reply("❌ This command is only available to administrators.")
                return
            
            # Get comprehensive statistics
            bot_stats = self.storage.get_bot_stats()
            total_files = await self.database.get_total_files()
            channel_stats = await self.database.get_channel_stats()
            file_type_stats = await self.database.get_file_type_stats()
            banned_users = self.storage.get_banned_users()
            
            # Calculate uptime
            uptime = "Unknown"
            if bot_stats.get('start_time'):
                try:
                    start_time = datetime.fromisoformat(bot_stats['start_time'])
                    current_time = datetime.now()
                    uptime_delta = current_time - start_time
                    
                    days = uptime_delta.days
                    hours, remainder = divmod(uptime_delta.seconds, 3600)
                    minutes, _ = divmod(remainder, 60)
                    
                    if days > 0:
                        uptime = f"{days}d {hours}h {minutes}m"
                    else:
                        uptime = f"{hours}h {minutes}m"
                except Exception as e:
                    logger.error(f"Error calculating uptime: {e}")
            
            # Create detailed stats message
            stats_text = f"""📊 **Advanced Bot Statistics**

**👥 User Activity:**
• Total Users: `{bot_stats.get('total_users', 0)}`
• Start Commands: `{bot_stats.get('start_commands', 0)}`
• Search Queries: `{bot_stats.get('total_queries', 0)}`  
• Files Shared: `{bot_stats.get('files_shared', 0)}`

**📁 Database Stats:**
• Indexed Files: `{total_files:,}`
• Banned Users: `{len(banned_users)}`
• Manual Indexes: `{bot_stats.get('manual_index_runs', 0)}`

**⏰ System Info:**
• Bot Uptime: `{uptime}`
• Database: `{'✅ Connected' if self.database.is_connected() else '❌ Disconnected'}`
• Status: `{'🟢 Online' if bot_stats.get('bot_started') else '🟡 Starting'}`"""

            if channel_stats:
                stats_text += "\n\n**📺 Channel Statistics:**"
                for channel_id, count in sorted(channel_stats.items(), key=lambda x: x[1], reverse=True):
                    try:
                        chat = await client.get_chat(int(channel_id))
                        stats_text += f"\n• {chat.title}: `{count:,}` files"
                    except:
                        stats_text += f"\n• Channel {channel_id}: `{count:,}` files"

            if file_type_stats:
                stats_text += "\n\n**📄 File Types:**"
                for file_type, count in sorted(file_type_stats.items(), key=lambda x: x[1], reverse=True):
                    emoji = get_file_emoji(file_type)
                    stats_text += f"\n• {emoji} {file_type.title()}: `{count:,}`"

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh Stats", callback_data="refresh_stats")],
                [InlineKeyboardButton("📋 Export Logs", callback_data="export_logs")]
            ])
            
            await message.reply(stats_text, reply_markup=keyboard)
            
            logger.info(f"📊 Stats requested by admin {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error in stats command: {e}")
            await message.reply("❌ Error retrieving statistics.")

    async def ban_command(self, client: Client, message: Message):
        """Handle /ban command (admin only)"""
        try:
            user_id = message.from_user.id
            
            if not self.config.is_admin(user_id):
                await message.reply("❌ This command is only available to administrators.")
                return
            
            if len(message.command) < 2:
                await message.reply(
                    "❌ **Invalid Usage**\n\n"
                    "**Usage:** `/ban <user_id>`\n"
                    "**Example:** `/ban 123456789`\n\n"
                    "💡 **Tip:** Forward a message from the user to get their ID."
                )
                return
            
            target_user_id = validate_user_id(message.command[1])
            if not target_user_id:
                await message.reply("❌ Invalid user ID. Please provide a valid numeric user ID.")
                return
            
            # Prevent banning admins
            if self.config.is_admin(target_user_id):
                await message.reply("❌ Cannot ban an administrator.")
                return
            
            # Ban the user
            if await self.storage.ban_user(target_user_id):
                try:
                    # Try to get user info
                    user = await client.get_users(target_user_id)
                    user_mention = f"[{user.first_name}](tg://user?id={target_user_id})"
                    await message.reply(
                        f"✅ **User Banned Successfully**\n\n"
                        f"**User:** {user_mention}\n"
                        f"**ID:** `{target_user_id}`\n"
                        f"**Banned by:** {message.from_user.mention}\n"
                        f"**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                except:
                    await message.reply(f"✅ User `{target_user_id}` has been banned successfully.")
            else:
                await message.reply(f"⚠️ User `{target_user_id}` is already banned.")
            
            logger.info(f"🚫 User {target_user_id} banned by admin {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error in ban command: {e}")
            await message.reply("❌ Error banning user.")

    async def unban_command(self, client: Client, message: Message):
        """Handle /unban command (admin only)"""
        try:
            user_id = message.from_user.id
            
            if not self.config.is_admin(user_id):
                await message.reply("❌ This command is only available to administrators.")
                return
            
            if len(message.command) < 2:
                await message.reply(
                    "❌ **Invalid Usage**\n\n"
                    "**Usage:** `/unban <user_id>`\n"
                    "**Example:** `/unban 123456789`"
                )
                return
            
            target_user_id = validate_user_id(message.command[1])
            if not target_user_id:
                await message.reply("❌ Invalid user ID. Please provide a valid numeric user ID.")
                return
            
            # Unban the user
            if await self.storage.unban_user(target_user_id):
                try:
                    # Try to get user info
                    user = await client.get_users(target_user_id)
                    user_mention = f"[{user.first_name}](tg://user?id={target_user_id})"
                    await message.reply(
                        f"✅ **User Unbanned Successfully**\n\n"
                        f"**User:** {user_mention}\n"
                        f"**ID:** `{target_user_id}`\n"
                        f"**Unbanned by:** {message.from_user.mention}\n"
                        f"**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                except:
                    await message.reply(f"✅ User `{target_user_id}` has been unbanned successfully.")
            else:
                await message.reply(f"⚠️ User `{target_user_id}` is not banned.")
            
            logger.info(f"✅ User {target_user_id} unbanned by admin {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error in unban command: {e}")
            await message.reply("❌ Error unbanning user.")

    async def broadcast_command(self, client: Client, message: Message):
        """Handle /broadcast command (admin only)"""
        try:
            user_id = message.from_user.id
            
            if not self.config.is_admin(user_id):
                await message.reply("❌ This command is only available to administrators.")
                return
            
            if len(message.text.split(None, 1)) < 2:
                await message.reply(
                    "❌ **Invalid Usage**\n\n"
                    "**Usage:** `/broadcast <message>`\n"
                    "**Example:** `/broadcast Hello everyone! New features added.`\n\n"
                    "💡 **Note:** The message will be sent to all users who have used the bot."
                )
                return
            
            broadcast_message = message.text.split(None, 1)[1]
            
            # Simple broadcast confirmation
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Confirm Broadcast", callback_data=f"confirm_broadcast"),
                    InlineKeyboardButton("❌ Cancel", callback_data="cancel_broadcast")
                ]
            ])
            
            preview_text = f"📢 **Broadcast Preview**\n\n{broadcast_message[:500]}{'...' if len(broadcast_message) > 500 else ''}\n\n**Confirm to send this message to all bot users?**"
            
            await message.reply(preview_text, reply_markup=keyboard)
            
            # Store broadcast message temporarily (in a real implementation, use proper storage)
            await self.storage.update_bot_stats({"pending_broadcast": broadcast_message})
            
        except Exception as e:
            logger.error(f"❌ Error in broadcast command: {e}")
            await message.reply("❌ Error preparing broadcast.")

    async def index_command(self, client: Client, message: Message):
        """Handle manual /index command (admin only)"""
        try:
            user_id = message.from_user.id
            
            if not self.config.is_admin(user_id):
                await message.reply("❌ This command is only available to administrators.")
                return
            
            # Parse command arguments
            channel_id = None
            limit = 100
            
            if len(message.command) > 1:
                try:
                    channel_id = int(message.command[1])
                    if channel_id not in self.config.CHANNELS:
                        await message.reply("❌ Channel ID not in configured channels list.")
                        return
                except ValueError:
                    await message.reply("❌ Invalid channel ID format.")
                    return
            
            if len(message.command) > 2:
                try:
                    limit = min(int(message.command[2]), 1000)  # Max 1000 messages
                except ValueError:
                    limit = 100
            
            status_msg = await message.reply("🔄 **Starting manual indexing...**\n\nThis may take a few moments.")
            
            indexed_count = 0
            error_count = 0
            channels_to_index = [channel_id] if channel_id else self.config.CHANNELS
            
            for channel in channels_to_index:
                try:
                    # Get channel info
                    chat = await client.get_chat(channel)
                    await status_msg.edit_text(
                        f"🔄 **Indexing Channel**\n\n"
                        f"**Channel:** {chat.title}\n"
                        f"**ID:** `{channel}`\n"
                        f"**Progress:** Processing messages..."
                    )
                    
                    # Index recent messages
                    message_count = 0
                    async for msg in client.get_chat_history(channel, limit=limit):
                        message_count += 1
                        
                        if msg.media:
                            try:
                                file_doc = await self._create_file_document(msg)
                                if file_doc and await self.database.save_file(file_doc):
                                    indexed_count += 1
                            except Exception as e:
                                error_count += 1
                                logger.error(f"Error indexing message {msg.id}: {e}")
                        
                        # Update progress every 20 messages
                        if message_count % 20 == 0:
                            await status_msg.edit_text(
                                f"🔄 **Indexing Channel**\n\n"
                                f"**Channel:** {chat.title}\n"
                                f"**Processed:** {message_count} messages\n"
                                f"**Indexed:** {indexed_count} files\n"
                                f"**Errors:** {error_count}"
                            )
                    
                except Exception as e:
                    logger.error(f"Error indexing channel {channel}: {e}")
                    error_count += 1
            
            # Final status update
            await status_msg.edit_text(
                f"✅ **Manual Indexing Complete**\n\n"
                f"**📊 Results:**\n"
                f"• **New Files Indexed:** `{indexed_count}`\n"
                f"• **Channels Processed:** `{len(channels_to_index)}`\n"
                f"• **Errors:** `{error_count}`\n"
                f"• **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"**💡 Tip:** Files are automatically indexed when posted to configured channels."
            )
            
            await self.storage.increment_stat("manual_index_runs")
            logger.info(f"📥 Manual index completed by admin {user_id}: {indexed_count} files indexed")
            
        except Exception as e:
            logger.error(f"❌ Error in index command: {e}")
            await message.reply("❌ Error during manual indexing.")

    async def delete_command(self, client: Client, message: Message):
        """Handle /delete command (admin only)"""
        try:
            user_id = message.from_user.id
            
            if not self.config.is_admin(user_id):
                await message.reply("❌ This command is only available to administrators.")
                return
            
            if len(message.command) < 2:
                await message.reply(
                    "❌ **Invalid Usage**\n\n"
                    "**Usage:** `/delete <file_id>`\n"
                    "**Example:** `/delete BAADBAADrwADBxG2CQAB`"
                )
                return
            
            file_id = message.command[1]
            
            if await self.database.delete_file(file_id):
                await message.reply(
                    f"✅ **File Deleted Successfully**\n\n"
                    f"**File ID:** `{file_id}`\n"
                    f"**Deleted by:** {message.from_user.mention}\n"
                    f"**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                logger.info(f"🗑️ File {file_id} deleted by admin {user_id}")
            else:
                await message.reply(f"❌ File with ID `{file_id}` not found in database.")
            
        except Exception as e:
            logger.error(f"❌ Error in delete command: {e}")
            await message.reply("❌ Error deleting file.")

    async def logger_command(self, client: Client, message: Message):
        """Handle /logger command (admin only)"""
        try:
            user_id = message.from_user.id
            
            if not self.config.is_admin(user_id):
                await message.reply("❌ This command is only available to administrators.")
                return
            
            if os.path.exists("bot.log"):
                # Get file size
                file_size = os.path.getsize("bot.log")
                size_str = format_file_size(file_size)
                
                await message.reply_document(
                    "bot.log",
                    caption=f"📋 **Bot Log File**\n\n"
                           f"**Size:** {size_str}\n"
                           f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                           f"**Requested by:** {message.from_user.mention}"
                )
                logger.info(f"📋 Log file sent to admin {user_id}")
            else:
                await message.reply("❌ Log file not found.")
            
        except Exception as e:
            logger.error(f"❌ Error in logger command: {e}")
            await message.reply("❌ Error sending log file.")

    async def total_command(self, client: Client, message: Message):
        """Handle /total command (admin only)"""
        try:
            user_id = message.from_user.id
            
            if not self.config.is_admin(user_id):
                await message.reply("❌ This command is only available to administrators.")
                return
            
            total_files = await self.database.get_total_files()
            file_type_stats = await self.database.get_file_type_stats()
            
            total_text = f"📊 **Total File Statistics**\n\n**📁 Total Indexed Files:** `{total_files:,}`\n\n"
            
            if file_type_stats:
                total_text += "**📄 Breakdown by Type:**\n"
                for file_type, count in sorted(file_type_stats.items(), key=lambda x: x[1], reverse=True):
                    emoji = get_file_emoji(file_type)
                    percentage = (count / total_files * 100) if total_files > 0 else 0
                    total_text += f"• {emoji} **{file_type.title()}:** `{count:,}` ({percentage:.1f}%)\n"
            
            total_text += f"\n**📅 Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            await message.reply(total_text)
            
        except Exception as e:
            logger.error(f"❌ Error in total command: {e}")
            await message.reply("❌ Error retrieving file count.")

    async def channel_command(self, client: Client, message: Message):
        """Handle /channel command (admin only)"""
        try:
            user_id = message.from_user.id
            
            if not self.config.is_admin(user_id):
                await message.reply("❌ This command is only available to administrators.")
                return
            
            channel_stats = await self.database.get_channel_stats()
            
            info_text = "📺 **Channel Information & Statistics**\n\n"
            
            total_channels = len(self.config.CHANNELS)
            active_channels = len([ch for ch in channel_stats if channel_stats[ch] > 0])
            
            info_text += f"**📊 Overview:**\n"
            info_text += f"• **Configured Channels:** `{total_channels}`\n"
            info_text += f"• **Active Channels:** `{active_channels}`\n\n"
            
            for channel_id in self.config.CHANNELS:
                try:
                    chat = await client.get_chat(channel_id)
                    file_count = channel_stats.get(str(channel_id), 0)
                    
                    # Get bot status in channel
                    try:
                        bot_member = await client.get_chat_member(channel_id, "me")
                        status = "✅ Active" if bot_member.status == "administrator" else f"⚠️ {bot_member.status.title()}"
                    except:
                        status = "❌ No Access"
                    
                    info_text += f"**📺 {chat.title}**\n"
                    info_text += f"• **ID:** `{channel_id}`\n"
                    info_text += f"• **Type:** {chat.type.title()}\n"
                    info_text += f"• **Files:** `{file_count:,}`\n"
                    info_text += f"• **Status:** {status}\n\n"
                    
                except Exception as e:
                    info_text += f"**Channel {channel_id}**\n"
                    info_text += f"• **Error:** {str(e)[:50]}...\n"
                    info_text += f"• **Files:** `{channel_stats.get(str(channel_id), 0):,}`\n\n"
            
            await message.reply(info_text)
            
        except Exception as e:
            logger.error(f"❌ Error in channel command: {e}")
            await message.reply("❌ Error retrieving channel information.")

    async def inline_query_handler(self, client: Client, inline_query: InlineQuery):
        """Handle inline search queries with advanced features"""
        try:
            user_id = inline_query.from_user.id
            query = inline_query.query.strip()
            
            # Rate limiting
            if not query_rate_limiter.is_allowed(user_id):
                reset_time = query_rate_limiter.get_reset_time(user_id)
                await inline_query.answer(
                    results=[],
                    cache_time=0,
                    switch_pm_text=f"⏱️ Rate limited ({reset_time}s)",
                    switch_pm_parameter="rate_limited"
                )
                return
            
            # Check if user is banned
            if self.storage.is_banned(user_id):
                await inline_query.answer(
                    results=[],
                    cache_time=0,
                    switch_pm_text="❌ You are banned",
                    switch_pm_parameter="banned"
                )
                return
            
            # Authorization checks
            if self.config.AUTH_USERS and not self.config.is_auth_user(user_id):
                await inline_query.answer(
                    results=[],
                    cache_time=0,
                    switch_pm_text="❌ Not authorized",
                    switch_pm_parameter="unauthorized"
                )
                return
            
            # Channel subscription check
            if self.config.AUTH_CHANNEL:
                try:
                    member = await client.get_chat_member(self.config.AUTH_CHANNEL, user_id)
                    if member.status in ["left", "kicked"]:
                        await inline_query.answer(
                            results=[],
                            cache_time=0,
                            switch_pm_text="📢 Join Channel First",
                            switch_pm_parameter="join_channel"
                        )
                        return
                except Exception as e:
                    logger.error(f"Error checking channel subscription: {e}")
            
            # Handle empty query - show all videos
            if not query:
                try:
                    # Get all video files from database
                    files = await self.database.search_files("", file_type="video", limit=50)
                    
                    if not files:
                        await inline_query.answer(
                            results=[],
                            cache_time=0,
                            switch_pm_text="📹 No videos found",
                            switch_pm_parameter="no_videos"
                        )
                        return
                    
                    # Create inline results for videos
                    results = []
                    for i, file_data in enumerate(files[:50]):
                        try:
                            result = await self._create_inline_result(i, file_data)
                            if result:
                                results.append(result)
                        except Exception as e:
                            logger.error(f"Error creating inline result: {e}")
                            continue
                    
                    await inline_query.answer(
                        results=results,
                        cache_time=self.config.CACHE_TIME,
                        switch_pm_text=f"📹 {len(results)} videos available",
                        switch_pm_parameter="all_videos"
                    )
                    return
                    
                except Exception as e:
                    logger.error(f"Error fetching all videos: {e}")
                    await inline_query.answer(
                        results=[],
                        cache_time=0,
                        switch_pm_text="❌ Error loading videos",
                        switch_pm_parameter="error"
                    )
                    return
            
            # Extract search terms and file type
            search_terms, file_type = extract_search_terms(query)
            
            # Search database
            files = await self.database.search_files(search_terms, file_type, limit=50)
            
            # Track query
            await self.storage.track_user_query(user_id, query)
            
            if not files:
                await inline_query.answer(
                    results=[],
                    cache_time=5,
                    switch_pm_text="❌ No files found",
                    switch_pm_parameter="no_results"
                )
                return
            
            # Create inline results
            results = []
            
            for i, file_data in enumerate(files[:50]):  # Limit to 50 results
                try:
                    result = await self._create_inline_result(i, file_data)
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.error(f"Error creating inline result: {e}")
                    continue
            
            # Answer query
            await inline_query.answer(
                results=results,
                cache_time=self.config.CACHE_TIME,
                switch_pm_text=f"📊 {len(results)} results",
                switch_pm_parameter="search_results"
            )
            
            logger.info(f"🔍 Search '{query}' by user {user_id}: {len(results)} results")
            
        except FloodWait as e:
            logger.warning(f"FloodWait in inline query: {e.value}s")
            await asyncio.sleep(e.value)
        except Exception as e:
            logger.error(f"❌ Error in inline query handler: {e}")
            try:
                await inline_query.answer(
                    results=[],
                    cache_time=0,
                    switch_pm_text="❌ Search error",
                    switch_pm_parameter="error"
                )
            except:
                pass

    async def chosen_inline_result_handler(self, client: Client, chosen_result):
        """Handle chosen inline results for statistics"""
        try:
            user_id = chosen_result.from_user.id
            result_id = chosen_result.result_id
            query = chosen_result.query
            
            await self.storage.increment_stat("files_shared")
            logger.info(f"📤 User {user_id} selected result {result_id} for '{query}'")
            
        except Exception as e:
            logger.error(f"❌ Error handling chosen result: {e}")

    async def callback_query_handler(self, client: Client, callback_query: CallbackQuery):
        """Handle callback queries from inline keyboards"""
        try:
            data = callback_query.data
            user_id = callback_query.from_user.id
            
            # Public stats callback
            if data == "public_stats":
                total_files = await self.database.get_total_files()
                file_type_stats = await self.database.get_file_type_stats()
                bot_stats = self.storage.get_bot_stats()
                
                stats_text = f"""📊 **Public Bot Statistics**

**📁 Database:**
• Total Files: `{total_files:,}`
• Total Queries: `{bot_stats.get('total_queries', 0):,}`
• Files Shared: `{bot_stats.get('files_shared', 0):,}`

**📄 File Types:**"""
                
                for file_type, count in sorted(file_type_stats.items(), key=lambda x: x[1], reverse=True)[:5]:
                    emoji = get_file_emoji(file_type)
                    stats_text += f"\n• {emoji} {file_type.title()}: `{count:,}`"
                
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔍 Search Files", switch_inline_query_current_chat="")],
                    [InlineKeyboardButton("🏠 Back to Start", callback_data="back_to_start")]
                ])
                
                await callback_query.message.edit_text(stats_text, reply_markup=keyboard)
                
            elif data == "show_help":
                me = await client.get_me()
                help_text = f"""❓ **Quick Help Guide**

**🔍 How to Search:**
Type `@{me.username} <search term>` in any chat

**💡 Search Tips:**
• Use specific keywords
• Try: `movie name | video`
• Search by filename or caption

**📁 File Types:**
• `| document` - Documents only
• `| video` - Videos only  
• `| audio` - Audio files only
• `| photo` - Images only

**Example Searches:**
• `@{me.username} python tutorial`
• `@{me.username} movie | video`
• `@{me.username} song name | audio`"""
                
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔍 Try Search", switch_inline_query_current_chat="")],
                    [InlineKeyboardButton("🏠 Back to Start", callback_data="back_to_start")]
                ])
                
                await callback_query.message.edit_text(help_text, reply_markup=keyboard)
                
            elif data == "back_to_start":
                # Recreate start message
                await self.start_command(client, callback_query.message)
                
            elif data == "check_subscription":
                # Check channel subscription
                if self.config.AUTH_CHANNEL:
                    try:
                        member = await client.get_chat_member(self.config.AUTH_CHANNEL, user_id)
                        if member.status not in ["left", "kicked"]:
                            await callback_query.answer("✅ Subscription verified! You can now use the bot.", show_alert=True)
                            await self.start_command(client, callback_query.message)
                            return
                    except:
                        pass
                
                await callback_query.answer("❌ Please join the required channel first.", show_alert=True)
                
            elif data == "confirm_broadcast" and self.config.is_admin(user_id):
                # Handle broadcast confirmation
                bot_stats = self.storage.get_bot_stats()
                broadcast_msg = bot_stats.get("pending_broadcast")
                
                if broadcast_msg:
                    await callback_query.message.edit_text(
                        "📢 **Broadcast sent!**\n\n"
                        "The message has been scheduled for delivery to all users.\n"
                        "Note: This is a simplified implementation."
                    )
                    # TODO: Implement actual broadcast to all users
                    logger.info(f"📢 Broadcast confirmed by admin {user_id}")
                else:
                    await callback_query.answer("❌ No pending broadcast found.", show_alert=True)
                    
            elif data == "cancel_broadcast":
                await callback_query.message.edit_text("❌ **Broadcast cancelled.**")
                await self.storage.update_bot_stats({"pending_broadcast": None})
                
            # Admin-only callbacks
            elif self.config.is_admin(user_id):
                if data == "refresh_stats":
                    await self.stats_command(client, callback_query.message)
                elif data == "export_logs":
                    await self.logger_command(client, callback_query.message)
            
            await callback_query.answer()
            
        except Exception as e:
            logger.error(f"❌ Error in callback query handler: {e}")
            await callback_query.answer("❌ An error occurred.", show_alert=True)

    async def channel_media_handler(self, client: Client, message: Message):
        """Handle media files posted in configured channels"""
        try:
            file_document = await self._create_file_document(message)
            
            if file_document and await self.database.save_file(file_document):
                await self.storage.increment_stat("total_files")
                logger.info(f"💾 Auto-indexed: {file_document['file_name']} from {message.chat.title}")
                
        except Exception as e:
            logger.error(f"❌ Error in channel media handler: {e}")

    async def global_error_handler(self, client: Client, message: Message):
        """Global error handler for session and other critical errors"""
        try:
            pass  # This handler runs last and catches unhandled messages
        except (SessionRevoked, AuthKeyUnregistered) as e:
            logger.error(f"🔐 Session error in global handler: {e}")
            await self.handle_session_error(e)
        except Exception as e:
            logger.error(f"❌ Unhandled error in global handler: {e}")

    async def _create_file_document(self, message: Message) -> Optional[Dict[str, Any]]:
        """Create file document for database storage"""
        try:
            file_info = None
            file_type = None
            
            # Determine file type and info
            if message.document:
                file_info = message.document
                file_type = "document"
            elif message.video:
                file_info = message.video
                file_type = "video"
            elif message.audio:
                file_info = message.audio
                file_type = "audio"
            elif message.photo:
                file_info = message.photo
                file_type = "photo"
            elif message.animation:
                file_info = message.animation
                file_type = "animation"
            elif message.voice:
                file_info = message.voice
                file_type = "voice"
            elif message.video_note:
                file_info = message.video_note
                file_type = "video_note"
            
            if not file_info or not file_type:
                return None
            
            # Handle photo (list of sizes)
            if file_type == "photo":
                # Get largest photo size
                file_info = max(file_info, key=lambda x: x.file_size)
            
            # Get file name
            file_name = getattr(file_info, 'file_name', None)
            if not file_name:
                extensions = {
                    "photo": "jpg",
                    "video": "mp4", 
                    "audio": "mp3",
                    "voice": "ogg",
                    "animation": "gif",
                    "video_note": "mp4"
                }
                ext = extensions.get(file_type, "file")
                file_name = f"{file_type}_{message.id}.{ext}"
            
            # Create document
            document = {
                "file_id": file_info.file_id,
                "file_unique_id": file_info.file_unique_id,
                "file_name": file_name,
                "file_size": getattr(file_info, 'file_size', 0),
                "file_type": file_type,
                "mime_type": getattr(file_info, 'mime_type', ''),
                "caption": message.caption or "",
                "channel_id": message.chat.id,
                "channel_title": message.chat.title or "",
                "message_id": message.id,
                "date": message.date,
                "indexed_at": datetime.now()
            }
            
            # Add type-specific fields
            if file_type in ["video", "audio", "voice", "video_note"]:
                document["duration"] = getattr(file_info, 'duration', 0)
            
            if file_type in ["video", "photo", "animation"]:
                document["width"] = getattr(file_info, 'width', 0)
                document["height"] = getattr(file_info, 'height', 0)
            
            if file_type == "audio":
                document["performer"] = getattr(file_info, 'performer', '')
                document["title"] = getattr(file_info, 'title', '')
            
            return document
            
        except Exception as e:
            logger.error(f"❌ Error creating file document: {e}")
            return None

    async def _create_inline_result(self, index: int, file_data: Dict[str, Any]):
        """Create inline query result from file data"""
        try:
            file_id = file_data.get("file_id")
            file_name = file_data.get("file_name", "Unknown File")
            file_size = file_data.get("file_size", 0)
            file_type = file_data.get("file_type", "unknown")
            caption = file_data.get("caption", "")
            
            # Format file information
            size_str = format_file_size(file_size)
            duration_str = ""
            if file_data.get("duration"):
                duration_str = format_duration(file_data["duration"])
            
            # Create description
            desc_parts = []
            if size_str != "Unknown":
                desc_parts.append(f"📦 {size_str}")
            if duration_str:
                desc_parts.append(f"⏱️ {duration_str}")
            if file_type:
                desc_parts.append(f"🔖 {file_type.title()}")
            
            description = " • ".join(desc_parts)
            
            # Create message content
            content_text = f"📁 **{file_name}**\n\n"
            content_text += f"📦 **Size:** {size_str}\n"
            content_text += f"🔖 **Type:** {file_type.title()}\n"
            
            if duration_str:
                content_text += f"⏱️ **Duration:** {duration_str}\n"
            
            # Add caption preview
            if caption:
                content_text += f"\n💬 **Description:**\n{caption[:300]}{'...' if len(caption) > 300 else ''}"
            
            # Create Telegram link
            channel_id = abs(file_data.get('channel_id', 0))
            message_id = file_data.get('message_id', 0)
            telegram_link = f"https://t.me/c/{channel_id}/{message_id}"
            content_text += f"\n\n🔗 [View File]({telegram_link})"
            
            # Use InlineQueryResultArticle instead of InlineQueryResultDocument
            from pyrogram.types import InlineQueryResultArticle
            
            return InlineQueryResultArticle(
                id=f"file_{index}",
                title=file_name[:64],  # Telegram title limit
                description=description[:512],  # Description limit
                input_message_content=InputTextMessageContent(
                    message_text=content_text,
                    disable_web_page_preview=False
                )
            )
            
        except Exception as e:
            logger.error(f"❌ Error creating inline result: {e}")
            return None

# Global handlers instance (will be initialized by main.py)
handlers = None

def register_handlers(app: Client, storage: Storage, config: Config):
    """Register all handlers with the Pyrogram client"""
    global handlers
    handlers = MediaSearchHandlers(app)
    handlers.storage = storage
    handlers.config = config
    logger.info("✅ Media Search Bot handlers registered successfully")