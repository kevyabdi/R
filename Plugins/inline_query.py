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


@app.on_message(filters.command("start") & filters.private)
async def start(client: Client, message):
    await message.reply_text(
        "ðŸ‘‹ Hello!\nSend me a file and Iâ€™ll save it.\nOr use inline mode to search for files anywhere in Telegram."
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
        await message.reply_text(f"âœ… File **'{file_data.get('file_name', 'Unknown File')}'** saved successfully!")
    except RPCError as e:
        logger.error(f"RPCError saving file: {e}")
        await message.reply_text(f"âŒ Error saving file: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error saving file: {e}")
        await message.reply_text("âš ï¸ An unexpected error occurred while saving the file.")

@app.on_inline_query()
async def inline_query(client: Client, inline_query: InlineQuery):
    query = (inline_query.query or "").strip()
    results = []
    try:
        db = await db_manager.get_database()
        # If no query -> show latest files (up to 50)
        search_q = query if query else ""
        files = await db.search_files(search_q, limit=50)

        for index, file_data in enumerate(files):
            try:
                file_name = file_data.get('file_name', f"File_{index}")
                file_size = file_data.get('file_size', 0)
                file_type = (file_data.get('file_type') or 'unknown').title()
                channel_id = int(file_data.get('channel_id', 0))
                message_id = int(file_data.get('message_id', 0))

                # Convert -100XXXX -> c/XXXX
                channel_id_str = str(abs(channel_id)).replace('-100', '') if str(channel_id).startswith('-100') else str(abs(channel_id))

                from pyrogram.types import InlineQueryResultArticle, InputTextMessageContent
                results.append(
                    InlineQueryResultArticle(
                        title=f"{file_name} â€¢ {file_type} â€¢ {file_size if isinstance(file_size, int) else file_size}",
                        description=f"Size: {file_size} | Type: {file_type}",
                        input_message_content=InputTextMessageContent(
                            message_text=(
                                f"ðŸ“ **{file_name}**\n\n"
                                f"ðŸ“¦ **Size:** {file_size}\n"
                                f"ðŸ”– **Type:** {file_type}\n\n"
                                f"**Link:** https://t.me/c/{channel_id_str}/{message_id}"
                            ),
                            disable_web_page_preview=False
                        )
                    )
                )
            except Exception as e:
                logger.error(f"Error creating inline result: {e}")
                continue

        await inline_query.answer(results, cache_time=5, is_personal=False)
    except Exception as e:
        logger.error(f"Inline query error: {e}")
        await inline_query.answer([], cache_time=5, is_personal=False) chosen_inline_result(client: Client, chosen_inline_result: ChosenInlineResult):
    logger.info(f"Chosen inline result: {chosen_inline_result.query} -> {chosen_inline_result.result_id}")

if __name__ == "__main__":
    logger.info("ðŸš€ Bot is starting...")
    app.run()