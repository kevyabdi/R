from pyrogram import Client, filters
from pyrogram.types import (
    InlineQuery, InlineQueryResultArticle,
    InputTextMessageContent, ChosenInlineResult
)
from pyrogram.errors import RPCError
from database_manager import db_manager
from utils import format_file_size, get_file_data
import logging
import os

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the bot instance from main
from main import app

@app.on_message(filters.command("start") & filters.private)
async def start(client: Client, message):
    await message.reply_text(
        "👋 Hello!\nSend me a file and I'll save it.\nOr use inline mode to search for files anywhere in Telegram."
    )

@app.on_message(filters.private & filters.document)
async def handle_document(client: Client, message):
    if not message.document:
        return

    try:
        file_data = await get_file_data(client, message)
        db = await db_manager.get_database()
        save_result = await db.save_file(file_data)
        if save_result is None:
            pass
        await message.reply_text(f"✅ File **'{file_data.get('file_name', 'Unknown File')}'** saved successfully!")
    except RPCError as e:
        logger.error(f"RPCError saving file: {e}")
        await message.reply_text(f"❌ Error saving file: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error saving file: {e}")
        await message.reply_text("⚠️ An unexpected error occurred while saving the file.")

@app.on_inline_query()
async def inline_query(client: Client, inline_query: InlineQuery):
    query = (inline_query.query or "").strip()
    results = []
    try:
        db = await db_manager.get_database()
        
        # If no query -> show latest files (up to 50)
        # If query provided -> search for matching files
        if query:
            # Search with partial matching - case insensitive
            files = await db.search_files(query, limit=50)
        else:
            # Show all recent files when no search query
            files = await db.search_files("", limit=50)

        for index, file_data in enumerate(files):
            try:
                file_name = file_data.get('file_name', f"File_{index}")
                file_size = file_data.get('file_size', 0)
                file_size_formatted = format_file_size(file_size) if isinstance(file_size, int) else str(file_size)
                file_type = (file_data.get('file_type') or 'unknown').title()
                channel_id = int(file_data.get('channel_id', 0))
                message_id = int(file_data.get('message_id', 0))

                # Convert -100XXXX -> c/XXXX for supergroups/channels
                if str(channel_id).startswith('-100'):
                    channel_id_str = str(channel_id)[4:]  # Remove -100 prefix
                else:
                    channel_id_str = str(abs(channel_id))

                # Get appropriate emoji for file type
                file_emoji = "📄"
                if file_type.lower() == "video":
                    file_emoji = "🎥"
                elif file_type.lower() == "audio":
                    file_emoji = "🎵"
                elif file_type.lower() == "photo":
                    file_emoji = "🖼️"
                elif file_type.lower() == "document":
                    file_emoji = "📄"
                elif file_type.lower() == "animation":
                    file_emoji = "🎬"

                results.append(
                    InlineQueryResultArticle(
                        id=f"file_{index}_{file_data.get('file_id', index)}",
                        title=f"{file_emoji} {file_name}",
                        description=f"Size: {file_size_formatted} | Type: {file_type}",
                        input_message_content=InputTextMessageContent(
                            message_text=(
                                f"📁 **{file_name}**\n\n"
                                f"📦 **Size:** {file_size_formatted}\n"
                                f"📖 **Type:** {file_type}\n\n"
                                f"**Link:** https://t.me/c/{channel_id_str}/{message_id}"
                            ),
                            disable_web_page_preview=False
                        )
                    )
                )
            except Exception as e:
                logger.error(f"Error creating inline result: {e}")
                continue

        # Provide appropriate switch_pm_text based on results
        if not query:
            switch_text = f"📊 {len(results)} files available"
        else:
            switch_text = f"🔍 {len(results)} results for '{query}'"

        await inline_query.answer(
            results, 
            cache_time=5, 
            is_personal=False,
            switch_pm_text=switch_text,
            switch_pm_parameter="search_results"
        )
        
    except Exception as e:
        logger.error(f"Inline query error: {e}")
        await inline_query.answer([], cache_time=5, is_personal=False)

@app.on_chosen_inline_result()
async def chosen_inline_result(client: Client, chosen_inline_result: ChosenInlineResult):
    logger.info(f"Chosen inline result: {chosen_inline_result.query} -> {chosen_inline_result.result_id}")

if __name__ == "__main__":
    logger.info("🚀 Bot is starting...")
    app.run()
