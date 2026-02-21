import asyncio

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from ai_agents import swarm_client, summary_agent
from context import build_context_variables
from database.repository import get_all_active_users, get_user_today_calories, get_user_meals_today, save_daily_summary
from services.telegram import send_telegram_message
from config import SUMMARY_HOUR, SUMMARY_MINUTE


def send_daily_summaries():
    """Generate and send daily calorie summaries to all users."""
    users = get_all_active_users()

    for user in users:
        chat_id = user["phone_number"]

        response = swarm_client.run(
            agent=summary_agent,
            messages=[{"role": "user", "content": "Generate my daily calorie summary."}],
            context_variables=build_context_variables(phone_number=chat_id),
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

        asyncio.run(send_telegram_message(chat_id, summary_text))


def setup_scheduler() -> BackgroundScheduler:
    """Configure APScheduler with daily summary job."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=send_daily_summaries,
        trigger=CronTrigger(hour=SUMMARY_HOUR, minute=SUMMARY_MINUTE),
        id="daily_summary",
        name="Send daily calorie summaries",
        replace_existing=True,
    )
    return scheduler
