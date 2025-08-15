from pyrogram import Client, filters
from pyrogram.types import (
    InlineQuery, InlineQueryResultDocument, InlineQueryResultArticle,
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

# Initialize bot
app = Client(
    "file_search_bot",
    api_id=os.environ.get("API_ID"),
    api_hash=os.environ.get("API_HASH"),
    bot_token=os.environ.get("BOT_TOKEN")
)

# Initialize database
db = Database(os.environ.get("DATABASE_URL"))

@app.on_message(filters.command("start") & filters.private)
async def start(client: Client, message):
    await message.reply_text(
        "Hello! Send me a file or use the inline mode to search for files."
    )

@app.on_message(filters.private & filters.document)
async def handle_document(client: Client, message):
    if not message.document:
        return

    try:
        file_data = await get_file_data(client, message)
        await db.save_file_data(file_data)
        await message.reply_text(f"File '{file_data.get('file_name', 'Unknown File')}' saved successfully!")
    except RPCError as e:
        logger.error(f"RPCError saving file: {e}")
        await message.reply_text(f"Error saving file: {e.message}")
    except Exception as e:
        logger.error(f"Unexpected error saving file: {e}")
        await message.reply_text("An unexpected error occurred while saving the file.")

@app.on_inline_query()
async def inline_query(client: Client, inline_query: InlineQuery):
    query = inline_query.query.strip()
    results = []

    if not query:
        return await inline_query.answer(results, cache_time=10)

    try:
        files = await db.search_files(query)
        for index, file_data in enumerate(files):
            try:
                file_name = file_data.get('file_name', 'Unknown File')
                if not file_name or file_name.strip() == '':
                    file_name = f"File_{file_data.get('message_id', index)}"

                # Create inline query result with proper content
                result = InlineQueryResultArticle(
                    id=f"file_{index}",
                    title=file_name[:100],
                    description=f"📦 {format_file_size(file_data.get('file_size', 0))} • 🔖 {file_data.get('file_type', 'unknown').title()}",
                    input_message_content=InputTextMessageContent(
                        message_text=f"📁 **{file_name}**\n\n📦 **Size:** {format_file_size(file_data.get('file_size', 0))}\n🔖 **Type:** {file_data.get('file_type', 'unknown').title()}\n\n**Link:** https://t.me/c/{abs(file_data.get('channel_id', 0))}/{file_data.get('message_id', 0)}",
                        disable_web_page_preview=False
                    ),
                    thumb_url="https://img.icons8.com/color/48/000000/file.png"
                )
                results.append(result)

            except Exception as e:
                logger.error(f"Error creating inline result for file {file_data.get('message_id', 'N/A')}: {e}")
                # Optionally, you could append a placeholder error result here

        await inline_query.answer(results, cache_time=60)

    except RPCError as e:
        logger.error(f"RPCError during inline query: {e}")
        await inline_query.answer(results, cache_time=10) # Return empty or cached results on error
    except Exception as e:
        logger.error(f"Unexpected error during inline query: {e}")
        await inline_query.answer(results, cache_time=10) # Return empty or cached results on error


@app.on_chosen_inline_result()
async def chosen_inline_result(client: Client, chosen_inline_result: ChosenInlineResult):
    # This function can be used to track which inline results are chosen by users
    logger.info(f"Chosen inline result: {chosen_inline_result.query} -> {chosen_inline_result.result_id}")

if __name__ == "__main__":
    app.run()