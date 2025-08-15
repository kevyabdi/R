from pyrogram import Client, filters
from pyrogram.types import (
    InlineQuery, InlineQueryResultArticle,
    InputTextMessageContent, ChosenInlineResult
)
from pyrogram.errors import RPCError
from database import Database
from utils import format_file_size, get_file_data
import logging
import os

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")

if not all([API_ID, API_HASH, BOT_TOKEN, DATABASE_URL]):
    logger.error("❌ Missing environment variables! Please set API_ID, API_HASH, BOT_TOKEN, DATABASE_URL")
    exit(1)

# Initialize bot
app = Client(
    "file_search_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Initialize database
db = Database(DATABASE_URL)

@app.on_message(filters.command("start") & filters.private)
async def start(client: Client, message):
    await message.reply_text(
        "👋 Hello!\nSend me a file and I’ll save it.\nOr use inline mode to search for files anywhere in Telegram."
    )

@app.on_message(filters.private & filters.document)
async def handle_document(client: Client, message):
    if not message.document:
        return

    try:
        file_data = await get_file_data(client, message)
        save_result = db.save_file_data(file_data)  # if db is async, make it: await db.save_file_data(file_data)
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
    query = inline_query.query.strip()
    results = []

    if not query:
        return await inline_query.answer(results, cache_time=10)

    try:
        files = db.search_files(query)  # if async: await db.search_files(query)
        for index, file_data in enumerate(files):
            try:
                file_name = file_data.get('file_name', f"File_{index}")
                file_size = file_data.get('file_size', 0)
                file_type = file_data.get('file_type', 'unknown').title()

                # Fix channel_id for t.me link
                channel_id_str = str(file_data.get('channel_id', '0')).replace("-100", "")
                message_id = file_data.get('message_id', 0)

                # Inline result
                results.append(
                    InlineQueryResultArticle(
                        id=f"file_{index}",
                        title=file_name[:100],
                        description=f"📦 {format_file_size(file_size)} • 🔖 {file_type}",
                        input_message_content=InputTextMessageContent(
                            message_text=(
                                f"📁 **{file_name}**\n\n"
                                f"📦 **Size:** {format_file_size(file_size)}\n"
                                f"🔖 **Type:** {file_type}\n\n"
                                f"**Link:** https://t.me/c/{channel_id_str}/{message_id}"
                            ),
                            disable_web_page_preview=False
                        ),
                        thumb_url="https://img.icons8.com/color/48/000000/file.png"
                    )
                )

            except Exception as e:
                logger.error(f"Error creating inline result: {e}")

        await inline_query.answer(results, cache_time=60)

    except RPCError as e:
        logger.error(f"RPCError during inline query: {e}")
        await inline_query.answer([], cache_time=10)
    except Exception as e:
        logger.error(f"Unexpected error during inline query: {e}")
        await inline_query.answer([], cache_time=10)

@app.on_chosen_inline_result()
async def chosen_inline_result(client: Client, chosen_inline_result: ChosenInlineResult):
    logger.info(f"Chosen inline result: {chosen_inline_result.query} -> {chosen_inline_result.result_id}")

if __name__ == "__main__":
    logger.info("🚀 Bot is starting...")
    app.run()
