import logging
logging.basicConfig(level=logging.INFO)
"""
Channel post handler for Media Search Bot
Handles automatic indexing of media files from configured channels
"""

from pyrogram import Client, filters
from pyrogram.types import Message
import logging
from datetime import datetime
from config import Config
from storage import Storage
from database_manager import db_manager

logger = logging.getLogger(__name__)

# Initialize components
config = Config()
storage = Storage()

def extract_file_info(message: Message):
    """Extract file information from message"""
    file_info = None
    file_type = None

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
    elif message.sticker:
        file_info = message.sticker
        file_type = "sticker"

    return file_info, file_type

def create_file_document(message: Message, file_info, file_type: str):
    """Create file document for database storage"""
    try:
        # Get file name
        file_name = getattr(file_info, 'file_name', None)
        if not file_name:
            if file_type == "photo":
                file_name = f"photo_{message.id}.jpg"
            elif file_type == "video":
                file_name = f"video_{message.id}.mp4"
            elif file_type == "audio":
                file_name = f"audio_{message.id}.mp3"
            elif file_type == "voice":
                file_name = f"voice_{message.id}.ogg"
            elif file_type == "animation":
                file_name = f"animation_{message.id}.gif"
            else:
                file_name = f"file_{message.id}"

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

        # Add type-specific information
        if file_type == "video":
            document.update({
                "duration": getattr(file_info, 'duration', 0),
                "width": getattr(file_info, 'width', 0),
                "height": getattr(file_info, 'height', 0)
            })
        elif file_type == "audio":
            document.update({
                "duration": getattr(file_info, 'duration', 0),
                "performer": getattr(file_info, 'performer', ''),
                "title": getattr(file_info, 'title', '')
            })
        elif file_type == "photo":
            # For photos, get the largest size
            if hasattr(file_info, '__iter__'):  # Photo sizes list
                largest = max(file_info, key=lambda x: x.file_size)
                document.update({
                    "width": largest.width,
                    "height": largest.height
                })
                document["file_id"] = largest.file_id
                document["file_unique_id"] = largest.file_unique_id
                document["file_size"] = largest.file_size

        return document

    except Exception as e:
        logger.error(f"❌ Error creating file document: {e}")
        return None

@Client.on_message(filters.chat(config.CHANNELS) & (
    filters.document | 
    filters.video | 
    filters.audio | 
    filters.photo | 
    filters.animation | 
    filters.voice | 
    filters.video_note
))
async def channel_media_handler(client: Client, message: Message):
    """Handle media files posted in configured channels"""
    try:
        logger.info(f"📥 Received message from channel {message.chat.id} ({message.chat.title})")

        # Extract file information
        file_info, file_type = extract_file_info(message)

        if not file_info or not file_type:
            logger.warning(f"⚠️ No media found in message {message.id} from {message.chat.title}")
            return

        logger.info(f"📁 Found {file_type} in message {message.id}")

        # Create file document
        file_document = create_file_document(message, file_info, file_type)

        if not file_document:
            logger.error(f"❌ Failed to create document for message {message.id}")
            return

        logger.info(f"📄 Created document for {file_document['file_name']}")

        # Save to database
        db = await db_manager.get_database()
        if await db.save_file(file_document):
            logger.info(f"💾 Successfully indexed {file_type}: {file_document['file_name']} from {message.chat.title}")
            await storage.increment_stat("total_files")
        else:
            logger.warning(f"🔄 File already indexed: {file_document['file_name']}")

    except Exception as e:
        logger.error(f"❌ Error handling channel media: {e}", exc_info=True)

@Client.on_message(filters.command("index") & filters.private)
async def manual_index_command(client: Client, message: Message):
    """Handle manual indexing command (admin only)"""
    try:
        user_id = message.from_user.id

        if not config.is_admin(user_id):
            await message.reply("❌ This command is only for admins.")
            return

        # Get channel ID if specified
        channel_id = None
        if len(message.command) > 1:
            try:
                channel_id = int(message.command[1])
                if channel_id not in config.CHANNELS:
                    await message.reply("❌ Channel not in configured channels list.")
                    return
            except ValueError:
                await message.reply("❌ Invalid channel ID.")
                return

        status_msg = await message.reply("🔄 Starting manual indexing...")

        indexed_count = 0
        channels_to_index = [channel_id] if channel_id else config.CHANNELS

        for channel in channels_to_index:
            try:
                await status_msg.edit_text(f"🔄 Indexing channel {channel}...")

                # Get recent messages from channel
                db = await db_manager.get_database()
                async for msg in client.get_chat_history(channel, limit=100):
                    if msg.media:
                        file_info, file_type = extract_file_info(msg)

                        if file_info and file_type:
                            file_document = create_file_document(msg, file_info, file_type)

                            if file_document and await db.save_file(file_document):
                                indexed_count += 1

            except Exception as e:
                logger.error(f"❌ Error indexing channel {channel}: {e}")
                continue

        await status_msg.edit_text(f"✅ Manual indexing completed!\n📊 Indexed {indexed_count} new files.")
        await storage.increment_stat("manual_index_runs")

    except Exception as e:
        logger.error(f"❌ Error in manual index command: {e}")
        await message.reply("❌ Error during manual indexing.")

# Handle channel info command
@Client.on_message(filters.command("channel") & filters.private)
async def channel_info_command(client: Client, message: Message):
    """Handle channel info command (admin only)"""
    try:
        user_id = message.from_user.id

        if not config.is_admin(user_id):
            await message.reply("❌ This command is only for admins.")
            return

        db = await db_manager.get_database()
        channel_stats = await db.get_channel_stats()

        info_text = "📺 **Channel Information**\n\n"

        for channel_id in config.CHANNELS:
            try:
                chat = await client.get_chat(channel_id)
                file_count = channel_stats.get(str(channel_id), 0)

                info_text += f"**{chat.title}**\n"
                info_text += f"• ID: `{channel_id}`\n"
                info_text += f"• Files: {file_count}\n"
                info_text += f"• Type: {chat.type}\n\n"

            except Exception as e:
                info_text += f"**Channel {channel_id}**\n"
                info_text += f"• Error: {str(e)}\n\n"

        await message.reply(info_text)

    except Exception as e:
        logger.error(f"❌ Error in channel info command: {e}")
        await message.reply("❌ Error retrieving channel information.")