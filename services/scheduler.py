import asyncio
import logging

from ai_agents import swarm_client, summary_agent
from context import build_context_variables
from database.repository import (
    get_all_active_users,
    get_user_today_calories,
    get_user_meals_today,
    get_user_today_macros,
    save_daily_summary,
    compute_daily_calorie_limit,
    get_users_needing_weight_nudge,
    update_weight_nudge_date,
)

logger = logging.getLogger(__name__)


async def daily_summary_job(context):
    """Generate and send daily calorie summaries to all users, then check weight nudges."""
    users = get_all_active_users()
    loop = asyncio.get_running_loop()

    for user in users:
        chat_id = user["phone_number"]
        try:
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
            macros = get_user_today_macros(user["id"])
            limit_data = compute_daily_calorie_limit(user["id"])

            save_daily_summary(
                user_id=user["id"],
                total_calories=total_calories,
                meal_count=len(meals),
                summary_text=summary_text,
                total_protein=macros["total_protein"],
                total_carbs=macros["total_carbs"],
                total_sugar=macros["total_sugar"],
                avg_health_rating=macros["avg_health_rating"],
                daily_calorie_limit=limit_data["daily_limit"],
            )

            await context.bot.send_message(chat_id=int(chat_id), text=summary_text)
            logger.info(f"Daily summary sent to {chat_id}")

        except Exception as e:
            logger.error(f"Failed to send daily summary to {chat_id}: {e}", exc_info=True)

    # Weight nudge check
    await _check_weight_nudges(context)


async def _check_weight_nudges(context):
    """Send weight recording reminders to users who haven't logged weight in 10+ days."""
    nudge_users = get_users_needing_weight_nudge()
    for user in nudge_users:
        chat_id = user["phone_number"]
        try:
            nudge_text = (
                "Hey! It's been a while since you recorded your weight. "
                "How about stepping on the scale today? "
                "Just tell me your weight and I'll log it for you."
            )
            await context.bot.send_message(chat_id=int(chat_id), text=nudge_text)
            update_weight_nudge_date(user["id"])
            logger.info(f"Weight nudge sent to {chat_id}")
        except Exception as e:
            logger.error(f"Failed to send weight nudge to {chat_id}: {e}", exc_info=True)
