import base64
import logging
import time

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import TELEGRAM_BOT_TOKEN
from ai_agents import swarm_client, chat_agent
from context import build_context_variables
from services.telegram import send_telegram_message, download_telegram_photo
from services.scheduler import setup_scheduler
from database.models import init_db
from database.repository import get_or_create_user, get_user_meals_today_summary

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory conversation store: {chat_id: {"messages": [...], "agent": Agent}}
conversations = {}


def _init_conversation(chat_id: int) -> dict:
    """Create a new conversation, seeding context with today's meals if any."""
    user = get_or_create_user(str(chat_id))
    meal_summary = get_user_meals_today_summary(user["id"])

    messages = []
    if meal_summary:
        messages.append({
            "role": "assistant",
            "content": (
                f"[Context restored] I see you have already logged meals today.\n"
                f"{meal_summary}\n"
                f"Your daily goal is {user['daily_goal']} calories. "
                f"How can I help you?"
            ),
        })

    conversations[chat_id] = {
        "messages": messages,
        "agent": chat_agent,
    }
    return conversations[chat_id]


def run_swarm_with_retry(agent, messages, context_variables, max_retries=3):
    """Run swarm client with retry logic for transient API failures."""
    for attempt in range(max_retries):
        try:
            return swarm_client.run(
                agent=agent,
                messages=messages,
                context_variables=context_variables,
            )
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.warning(
                    f"Swarm API call failed (attempt {attempt + 1}/{max_retries}): {e}. "
                    f"Retrying in {wait_time}s..."
                )
                time.sleep(wait_time)
            else:
                raise


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command -- greet the user."""
    chat_id = update.effective_chat.id

    conv = _init_conversation(chat_id)
    context_variables = build_context_variables(phone_number=str(chat_id))

    user_message = {"role": "user", "content": "Hi! What can you do?"}
    conv["messages"].append(user_message)

    try:
        response = run_swarm_with_retry(
            agent=conv["agent"],
            messages=conv["messages"],
            context_variables=context_variables,
        )
        reply_text = response.messages[-1]["content"]
        conv["agent"] = response.agent
        conv["messages"].extend(response.messages)
        await send_telegram_message(chat_id, reply_text)
    except Exception as e:
        logger.error(f"Error in /start for {chat_id}: {e}")
        await send_telegram_message(chat_id, "Something went wrong. Please try again.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text messages."""
    chat_id = update.effective_chat.id
    text = update.message.text

    if chat_id not in conversations:
        _init_conversation(chat_id)

    conv = conversations[chat_id]
    context_variables = build_context_variables(phone_number=str(chat_id))

    user_message = {"role": "user", "content": text}
    conv["messages"].append(user_message)

    try:
        response = run_swarm_with_retry(
            agent=conv["agent"],
            messages=conv["messages"],
            context_variables=context_variables,
        )
        reply_text = response.messages[-1]["content"]
        conv["agent"] = response.agent
        conv["messages"].extend(response.messages)

        if len(conv["messages"]) > 40:
            conv["messages"] = conv["messages"][-20:]

        await send_telegram_message(chat_id, reply_text)

    except Exception as e:
        logger.error(f"Error processing message from {chat_id}: {e}")
        await send_telegram_message(
            chat_id,
            "Something went wrong processing your message. Please try again.",
        )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming photo messages."""
    chat_id = update.effective_chat.id
    caption = update.message.caption or "Please analyze this food."

    # Telegram sends multiple photo sizes; take the largest (last in the list)
    photo = update.message.photo[-1]
    photo_file = await photo.get_file()
    image_bytes = await download_telegram_photo(photo_file)
    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    if chat_id not in conversations:
        _init_conversation(chat_id)

    conv = conversations[chat_id]
    context_variables = build_context_variables(
        phone_number=str(chat_id),
        media_id=photo_file.file_id,
    )

    user_message = {
        "role": "user",
        "content": [
            {"type": "text", "text": caption},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{b64_image}"
                },
            },
        ],
    }
    conv["messages"].append(user_message)

    try:
        response = run_swarm_with_retry(
            agent=conv["agent"],
            messages=conv["messages"],
            context_variables=context_variables,
        )
        reply_text = response.messages[-1]["content"]
        conv["agent"] = response.agent
        conv["messages"].extend(response.messages)

        if len(conv["messages"]) > 40:
            conv["messages"] = conv["messages"][-20:]

        await send_telegram_message(chat_id, reply_text)

    except Exception as e:
        logger.error(f"Error processing photo from {chat_id}: {e}")
        await send_telegram_message(
            chat_id,
            "Something went wrong processing your photo. Please try again.",
        )


async def handle_unsupported(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unsupported message types."""
    chat_id = update.effective_chat.id
    await send_telegram_message(
        chat_id,
        "Sorry, I can only handle text and photo messages right now.",
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors in the telegram bot."""
    logger.error(f"Exception while handling an update: {context.error}")

    if isinstance(update, Update) and update.effective_chat:
        try:
            await send_telegram_message(
                update.effective_chat.id,
                "An error occurred. Please try again in a moment.",
            )
        except Exception:
            pass


def main():
    init_db()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(
        MessageHandler(
            ~filters.TEXT & ~filters.PHOTO & ~filters.COMMAND,
            handle_unsupported,
        )
    )
    app.add_error_handler(error_handler)

    # Set up scheduler for daily summaries
    scheduler = setup_scheduler()
    scheduler.start()

    logger.info("Personal Messaging Assistant bot started (polling)")
    app.run_polling(
        drop_pending_updates=False,
        poll_interval=2.0,
        timeout=30,
        read_timeout=30,
        write_timeout=30,
        connect_timeout=30,
        pool_timeout=30,
    )


def main_with_restart():
    """Run main() in a loop, restarting on crash."""
    while True:
        try:
            main()
        except KeyboardInterrupt:
            logger.info("Bot stopped by user.")
            break
        except Exception as e:
            logger.error(f"Bot crashed: {e}. Restarting in 10 seconds...")
            time.sleep(10)


if __name__ == "__main__":
    main_with_restart()
