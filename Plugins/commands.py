import logging
import os
import asyncio
from datetime import datetime
from telegram import (
    Update,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    InlineQueryHandler,
)
from telegram.constants import ParseMode
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))


def get_logger():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    return logging.getLogger(__name__)


logger = get_logger()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}!",
        reply_markup=context.bot_data.get("keyboard"),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = """
Here are the available commands:
/start - Start the bot
/help - Show this help message
/ban <user> - Ban a user
/unban <user> - Unban a user
/broadcast <message> - Send a message to all users
/stats - Show bot statistics
"""
    await update.message.reply_text(help_text)


async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user_id_to_ban = int(context.args[0])
        reason = " ".join(context.args[1:]) or "No reason provided"
        await context.bot.ban_chat_member(
            chat_id=update.effective_chat.id, user_id=user_id_to_ban
        )
        await update.message.reply_text(
            f"✅ User {user_id_to_ban} banned.\nReason: {reason}\nBy: {update.effective_user.first_name}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /ban <user_id> [reason]")
    except Exception as e:
        logger.error(e)
        await update.message.reply_text(f"Error banning user: {e}")


async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user_id_to_unban = int(context.args[0])
        await context.bot.unban_chat_member(
            chat_id=update.effective_chat.id, user_id=user_id_to_unban
        )
        await update.message.reply_text(f"✅ User {user_id_to_unban} unbanned.")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /unban <user_id>")
    except Exception as e:
        logger.error(e)
        await update.message.reply_text(f"Error unbanning user: {e}")


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return
    broadcast_message = " ".join(context.args)
    if not broadcast_message:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    context.user_data["broadcast_message"] = broadcast_message
    keyboard = [[InlineKeyboardButton("Confirm", callback_data="confirm_broadcast")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"📢 Broadcast Preview:\n\n{broadcast_message}", reply_markup=reply_markup)


async def broadcast_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    broadcast_message = context.user_data.get("broadcast_message")
    if not broadcast_message:
        await query.edit_message_text("Broadcast message not found.")
        return
    user_ids = [ADMIN_ID]  # Replace with DB users
    sent_count = 0
    for user_id in user_ids:
        try:
            await context.bot.send_message(chat_id=user_id, text=broadcast_message)
            sent_count += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Failed to send to {user_id}: {e}")
    await query.edit_message_text(f"✅ Broadcast sent to {sent_count} users.")
    context.user_data.pop("broadcast_message", None)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    total_users = 100
    active_users = 50
    await update.message.reply_text(f"📊 Bot Statistics:\nTotal Users: {total_users}\nActive Users: {active_users}")


async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.inline_query.query
    if not query:
        return
    results = [
        InlineQueryResultArticle(
            id=query.upper(),
            title="Search Results",
            input_message_content=InputTextMessageContent(f"Searching for: {query}"),
        ),
    ]
    await update.inline_query.answer(results)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Update {update} caused error {context.error}")


def main() -> None:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("ban", ban_user))
    application.add_handler(CommandHandler("unban", unban_user))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CallbackQueryHandler(broadcast_confirm, pattern="^confirm_broadcast$"))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(InlineQueryHandler(inline_query))
    application.add_error_handler(error_handler)
    application.bot_data["keyboard"] = ReplyKeyboardMarkup(
        [[KeyboardButton("/help"), KeyboardButton("/stats")]], resize_keyboard=True
    )
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
