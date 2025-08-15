import logging
import os
from datetime import datetime

from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
    InlineQueryHandler,
)

from telegram.constants import ParseMode

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))


def get_logger():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logger = logging.getLogger(__name__)
    return logger


logger = get_logger()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}!",
        reply_markup=context.bot_data.get("keyboard"),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
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
    """Ban a user."""
    try:
        user_id_to_ban = int(context.args[0])
        reason = " ".join(context.args[1:]) or "No reason provided"
        user_mention = f"User ID: {user_id_to_ban}"
        try:
            banned_user = await context.bot.ban_chat_member(
                chat_id=update.effective_chat.id, user_id=user_id_to_ban
            )

            target_user_id = user_id_to_ban
            await update.message.reply(
                f"✅ User Banned Successfully\n\n"
                f"User: {user_mention}\n"
                f"ID: {target_user_id}\n"
                f"Banned by: {message.from_user.first_name}\n"
                f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            logger.info(f"User {user_id_to_ban} banned by {update.effective_user.id}")
        except Exception as e:
            logger.error(f"Error banning user {user_id_to_ban}: {e}")
            await update.message.reply_text(f"Error banning user: {e}")

    except (IndexError, ValueError):
        await update.message.reply_text(
            "Usage: /ban <user_id> [reason]\n"
            "Example: /ban 123456789 Spamming"
        )


async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Unban a user."""
    try:
        user_id_to_unban = int(context.args[0])
        user_mention = f"User ID: {user_id_to_unban}"
        try:
            await context.bot.unban_chat_member(
                chat_id=update.effective_chat.id, user_id=user_id_to_unban
            )
            await update.message.reply_text(f"✅ User {user_mention} unbanned successfully.")
            logger.info(f"User {user_id_to_unban} unbanned by {update.effective_user.id}")
        except Exception as e:
            logger.error(f"Error unbanning user {user_id_to_unban}: {e}")
            await update.message.reply_text(f"Error unbanning user: {e}")

    except (IndexError, ValueError):
        await update.message.reply_text(
            "Usage: /unban <user_id>\n"
            "Example: /unban 123456789"
        )


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message to all users."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    broadcast_message = " ".join(context.args)
    if not broadcast_message:
        await update.message.reply_text("Usage: /broadcast <message>")
        return

    keyboard = [[InlineKeyboardButton("Confirm", callback_data="confirm_broadcast")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    preview_text = (
        f"📢 Broadcast Preview\n\n"
        f"{broadcast_message[:500]}{'...' if len(broadcast_message) > 500 else ''}\n\n"
        f"Confirm to send this message to all bot users?"
    )
    await update.message.reply_text(preview_text, reply_markup=reply_markup)


async def broadcast_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Confirm and send broadcast message."""
    query = update.callback_query
    await query.answer()

    # Retrieve broadcast message from user data
    broadcast_message = context.user_data.get("broadcast_message")

    if not broadcast_message:
        await query.edit_message_text("Broadcast message not found. Please try again.")
        return

    # Get all user IDs from the database
    # Replace this with your actual database query to get user IDs
    user_ids = [ADMIN_ID]  # Example: just the admin for now

    sent_count = 0
    for user_id in user_ids:
        try:
            await context.bot.send_message(chat_id=user_id, text=broadcast_message)
            sent_count += 1
            # Add a small delay to avoid hitting rate limits
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Failed to send broadcast to {user_id}: {e}")

    await query.edit_message_text(
        f"Broadcast sent to {sent_count} users.\n"
        f"Original message: {broadcast_message}"
    )
    # Clear the broadcast message from user data
    context.user_data.pop("broadcast_message", None)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show bot statistics."""
    # Replace this with your actual database query to get statistics
    total_users = 100  # Example statistics
    active_users = 50

    stats_text = f"Bot Statistics:\n\nTotal Users: {total_users}\nActive Users: {active_users}"
    await update.message.reply_text(stats_text)


async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline queries."""
    query = update.inline_query.query

    if not query:
        return

    results = [
        InlineQueryResultArticle(
            id=query.upper(),
            title="Search Results",
            input_message_content=InputTextMessageContent(
                f"Searching for: {query}"
            ),
        ),
    ]

    await update.inline_query.answer(results)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log Errors caused by Updates."""
    logger.error(f"Update {update} caused error {context.error}")


def main() -> None:
    """Start the bot."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("ban", ban_user))
    application.add_handler(CommandHandler("unban", unban_user))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CallbackQueryHandler(broadcast_confirm, pattern="^confirm_broadcast$"))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(InlineQueryHandler(inline_query))

    # Register error handler
    application.add_error_handler(error_handler)

    # Add a default keyboard for the start command
    context.bot_data["keyboard"] = ReplyKeyboardMarkup(
        [[KeyboardButton("/help"), KeyboardButton("/stats")]], resize_keyboard=True
    )

    # Start the Bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()