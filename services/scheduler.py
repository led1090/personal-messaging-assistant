import asyncio
import logging

from ai_agents import swarm_client, summary_agent
from context import build_context_variables
from database.repository import get_all_active_users, get_user_today_calories, get_user_meals_today, save_daily_summary

logger = logging.getLogger(__name__)


async def daily_summary_job(context):
    """Generate and send daily calorie summaries to all users.

    Runs inside the bot's event loop via python-telegram-bot's JobQueue.
    """
    users = get_all_active_users()
    loop = asyncio.get_running_loop()

    for user in users:
        chat_id = user["phone_number"]
        try:
            # Run blocking swarm call in a thread executor
            response = await loop.run_in_executor(
                None,
                lambda cid=chat_id: swarm_client.run(
                    agent=summary_agent,
                    messages=[{"role": "user", "content": "Generate my daily calorie summary."}],
                    context_variables=build_context_variables(phone_number=cid),
                ),
            )

            summary_text = response.messages[-1]["content"]

            total_calories = get_user_today_calories(user["id"])
            meals = get_user_meals_today(user["id"])

            save_daily_summary(
                user_id=user["id"],
                total_calories=total_calories,
                meal_count=len(meals),
                summary_text=summary_text,
            )

            await context.bot.send_message(chat_id=int(chat_id), text=summary_text)
            logger.info(f"Daily summary sent to {chat_id}")

        except Exception as e:
            logger.error(f"Failed to send daily summary to {chat_id}: {e}", exc_info=True)
