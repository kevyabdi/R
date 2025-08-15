"""
Command handlers for Media Search Bot
Handles admin commands and user interactions
"""

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import logging
import os
import asyncio
from config import Config
from storage import Storage
from database_manager import db_manager

logger = logging.getLogger(__name__)

# Initialize components
config = Config()
storage = Storage()

@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    """Handle /start command"""
    try:
        user_id = message.from_user.id
        
        # Check if user is banned
        if storage.is_banned(user_id):
            await message.reply("❌ You are banned from using this bot.")
            return
        
        # Check authorization
        if config.AUTH_USERS and not config.is_auth_user(user_id):
            await message.reply("❌ You are not authorized to use this bot.")
            return
        
        # Check channel subscription if required
        if config.AUTH_CHANNEL:
            try:
                member = await client.get_chat_member(config.AUTH_CHANNEL, user_id)
                if member.status in ["left", "kicked"]:
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("Join Channel", url=f"https://t.me/{config.AUTH_CHANNEL.replace('@', '')}")]
                    ])
                    await message.reply(config.INVITE_MSG, reply_markup=keyboard)
                    return
            except Exception as e:
                logger.error(f"Error checking channel membership: {e}")
        
        # Get bot info
        me = await client.get_me()
        username = me.username
        
        # Create start message with inline keyboard
        start_text = config.START_MSG.format(username=f"@{username}")
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Search Inline", switch_inline_query_current_chat="")],
            [InlineKeyboardButton("📊 Bot Stats", callback_data="show_stats")],
            [InlineKeyboardButton("❓ Help", callback_data="show_help")]
        ])
        
        await message.reply(start_text, reply_markup=keyboard, disable_web_page_preview=True)
        
        # Update statistics
        await storage.increment_stat("start_commands")
        
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await message.reply("❌ An error occurred. Please try again later.")

@Client.on_message(filters.command("stats") & filters.private)
async def stats_command(client: Client, message: Message):
    """Handle /stats command (admin only)"""
    try:
        user_id = message.from_user.id
        
        if not config.is_admin(user_id):
            await message.reply("❌ This command is only for admins.")
            return
        
        # Get statistics
        bot_stats = storage.get_bot_stats()
        db = await db_manager.get_database()
        total_files = await db.get_total_files()
        channel_stats = await db.get_channel_stats()
        file_type_stats = await db.get_file_type_stats()
        banned_users = storage.get_banned_users()
        
        # Create stats message
        stats_text = f"""📊 **Bot Statistics**

👥 **Users**: {bot_stats.get('total_users', 0)}
🔍 **Total Queries**: {bot_stats.get('total_queries', 0)}
📁 **Indexed Files**: {total_files}
🚫 **Banned Users**: {len(banned_users)}

📺 **Files by Channel**:"""
        
        for channel_id, count in channel_stats.items():
            stats_text += f"\n• Channel {channel_id}: {count} files"
        
        stats_text += "\n\n📄 **Files by Type**:"
        for file_type, count in file_type_stats.items():
            stats_text += f"\n• {file_type.title()}: {count} files"
        
        if bot_stats.get('start_time'):
            stats_text += f"\n\n⏰ **Bot Started**: {bot_stats['start_time'][:19]}"
        
        await message.reply(stats_text)
        
    except Exception as e:
        logger.error(f"Error in stats command: {e}")
        await message.reply("❌ Error retrieving statistics.")

@Client.on_message(filters.command("ban") & filters.private)
async def ban_command(client: Client, message: Message):
    """Handle /ban command (admin only)"""
    try:
        user_id = message.from_user.id
        
        if not config.is_admin(user_id):
            await message.reply("❌ This command is only for admins.")
            return
        
        # Get user ID to ban
        if len(message.command) < 2:
            await message.reply("❌ Please provide a user ID to ban.\nUsage: `/ban <user_id>`")
            return
        
        try:
            target_user_id = int(message.command[1])
        except ValueError:
            await message.reply("❌ Invalid user ID. Please provide a numeric user ID.")
            return
        
        # Don't allow banning admins
        if config.is_admin(target_user_id):
            await message.reply("❌ Cannot ban an admin.")
            return
        
        # Ban the user
        if await storage.ban_user(target_user_id):
            await message.reply(f"✅ User {target_user_id} has been banned.")
        else:
            await message.reply(f"⚠️ User {target_user_id} is already banned.")
        
    except Exception as e:
        logger.error(f"Error in ban command: {e}")
        await message.reply("❌ Error banning user.")

@Client.on_message(filters.command("unban") & filters.private)
async def unban_command(client: Client, message: Message):
    """Handle /unban command (admin only)"""
    try:
        user_id = message.from_user.id
        
        if not config.is_admin(user_id):
            await message.reply("❌ This command is only for admins.")
            return
        
        # Get user ID to unban
        if len(message.command) < 2:
            await message.reply("❌ Please provide a user ID to unban.\nUsage: `/unban <user_id>`")
            return
        
        try:
            target_user_id = int(message.command[1])
        except ValueError:
            await message.reply("❌ Invalid user ID. Please provide a numeric user ID.")
            return
        
        # Unban the user
        if await storage.unban_user(target_user_id):
            await message.reply(f"✅ User {target_user_id} has been unbanned.")
        else:
            await message.reply(f"⚠️ User {target_user_id} is not banned.")
        
    except Exception as e:
        logger.error(f"Error in unban command: {e}")
        await message.reply("❌ Error unbanning user.")

@Client.on_message(filters.command("broadcast") & filters.private)
async def broadcast_command(client: Client, message: Message):
    """Handle /broadcast command (admin only)"""
    try:
        user_id = message.from_user.id
        
        if not config.is_admin(user_id):
            await message.reply("❌ This command is only for admins.")
            return
        
        # Get broadcast message
        if len(message.text.split(None, 1)) < 2:
            await message.reply("❌ Please provide a message to broadcast.\nUsage: `/broadcast <message>`")
            return
        
        broadcast_text = message.text.split(None, 1)[1]
        
        # This is a simplified broadcast - in a full implementation,
        # you would need to maintain a list of all users who have used the bot
        await message.reply("📢 Broadcast feature is available but requires user database implementation.")
        
        # TODO: Implement user collection and broadcast functionality
        # For now, just confirm the command was received
        logger.info(f"Broadcast requested by admin {user_id}: {broadcast_text[:50]}...")
        
    except Exception as e:
        logger.error(f"Error in broadcast command: {e}")
        await message.reply("❌ Error processing broadcast.")

@Client.on_message(filters.command("total") & filters.private)
async def total_command(client: Client, message: Message):
    """Handle /total command (admin only)"""
    try:
        user_id = message.from_user.id
        
        if not config.is_admin(user_id):
            await message.reply("❌ This command is only for admins.")
            return
        
        db = await db_manager.get_database()
        total_files = await db.get_total_files()
        await message.reply(f"📊 **Total Indexed Files**: {total_files}")
        
    except Exception as e:
        logger.error(f"Error in total command: {e}")
        await message.reply("❌ Error getting file count.")

@Client.on_message(filters.command("test") & filters.private)
async def test_command(client: Client, message: Message):
    """Handle /test command (admin only) - Test channel access and database"""
    try:
        user_id = message.from_user.id
        
        if not config.is_admin(user_id):
            await message.reply("❌ This command is only for admins.")
            return
        
        test_msg = await message.reply("🔍 Testing bot status...")
        
        results = []
        
        # Test database connection
        try:
            db = await db_manager.get_database()
            total_files = await db.get_total_files()
            results.append("✅ **Database Status**")
            results.append(f"   • Connection: Active")
            results.append(f"   • Total Files: {total_files}")
        except Exception as e:
            results.append("❌ **Database Status**")
            results.append(f"   • Error: {str(e)}")
        
        results.append("")
        
        # Test channel access
        for channel_id in config.CHANNELS:
            try:
                chat = await client.get_chat(channel_id)
                member = await client.get_chat_member(channel_id, "me")
                
                results.append(f"✅ **{chat.title}**")
                results.append(f"   • ID: `{channel_id}`")
                results.append(f"   • Type: {chat.type}")
                results.append(f"   • Bot Status: {member.status}")
                results.append(f"   • Can Read: {'✅' if member.privileges and member.privileges.can_read_messages else '❌'}")
                
            except Exception as e:
                results.append(f"❌ **Channel {channel_id}**")
                results.append(f"   • Error: {str(e)}")
        
        if not config.CHANNELS:
            results.append("⚠️ No channels configured")
        
        response = "🔍 **Bot Status Test**\n\n" + "\n".join(results)
        await test_msg.edit_text(response)
        
    except Exception as e:
        logger.error(f"Error in test command: {e}")
        await message.reply("❌ Error testing bot status.")

@Client.on_message(filters.command("delete") & filters.private)
async def delete_command(client: Client, message: Message):
    """Handle /delete command (admin only)"""
    try:
        user_id = message.from_user.id
        
        if not config.is_admin(user_id):
            await message.reply("❌ This command is only for admins.")
            return
        
        if len(message.command) < 2:
            await message.reply("❌ Please provide a file ID to delete.\nUsage: `/delete <file_id>`")
            return
        
        file_id = message.command[1]
        
        db = await db_manager.get_database()
        if await db.delete_file(file_id):
            await message.reply(f"✅ File {file_id} deleted successfully.")
        else:
            await message.reply(f"❌ File {file_id} not found.")
        
    except Exception as e:
        logger.error(f"Error in delete command: {e}")
        await message.reply("❌ Error deleting file.")

@Client.on_message(filters.command("logger") & filters.private)
async def logger_command(client: Client, message: Message):
    """Handle /logger command (admin only)"""
    try:
        user_id = message.from_user.id
        
        if not config.is_admin(user_id):
            await message.reply("❌ This command is only for admins.")
            return
        
        # Send log file if it exists
        if os.path.exists("bot.log"):
            await message.reply_document("bot.log", caption="📋 Bot Log File")
        else:
            await message.reply("❌ Log file not found.")
        
    except Exception as e:
        logger.error(f"Error in logger command: {e}")
        await message.reply("❌ Error sending log file.")

# Callback query handlers
@Client.on_callback_query(filters.regex("show_stats"))
async def show_public_stats(client: Client, callback_query):
    """Show public statistics"""
    try:
        db = await db_manager.get_database()
        total_files = await db.get_total_files()
        file_type_stats = await db.get_file_type_stats()
        
        stats_text = f"""📊 **Public Statistics**

📁 **Total Files**: {total_files}

📄 **File Types**:"""
        
        for file_type, count in file_type_stats.items():
            stats_text += f"\n• {file_type.title()}: {count}"
        
        await callback_query.answer()
        await callback_query.message.edit_text(stats_text)
        
    except Exception as e:
        logger.error(f"Error showing public stats: {e}")
        await callback_query.answer("❌ Error loading statistics", show_alert=True)

@Client.on_callback_query(filters.regex("show_help"))
async def show_help(client: Client, callback_query):
    """Show help information"""
    try:
        me = await client.get_me()
        help_text = f"""❓ **How to Use {me.first_name}**

🔍 **Search for Files:**
• Type `@{me.username} <search term>` in any chat
• Example: `@{me.username} python tutorial`
• You can search by filename or caption

📁 **Supported File Types:**
• Documents (.pdf, .doc, .zip, etc.)
• Videos (.mp4, .avi, .mkv, etc.)
• Audio (.mp3, .wav, .flac, etc.)
• Photos (.jpg, .png, .gif, etc.)

🔎 **Search Tips:**
• Use specific keywords for better results
• Try different variations of your search term
• You can search using `filename | filetype` format

**Example**: `Avengers | video`

Need more help? Contact the bot administrators."""
        
        await callback_query.answer()
        await callback_query.message.edit_text(help_text)
        
    except Exception as e:
        logger.error(f"Error showing help: {e}")
        await callback_query.answer("❌ Error loading help", show_alert=True)
