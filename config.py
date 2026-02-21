import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot API
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Database
DATABASE_PATH = os.getenv("DATABASE_PATH", "healthenforcer.db")

# Scheduler
SUMMARY_HOUR = int(os.getenv("SUMMARY_HOUR", "21"))
SUMMARY_MINUTE = int(os.getenv("SUMMARY_MINUTE", "0"))
