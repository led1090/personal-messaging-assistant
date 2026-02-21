import logging
from telegram import Bot
from config import TELEGRAM_BOT_TOKEN

logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_BOT_TOKEN)


async def send_telegram_message(chat_id, text: str):
    """Send a text message via Telegram Bot API.

    Telegram has a 4096-character limit per message.
    If the text is longer, split it into chunks.
    """
    max_length = 4096
    if len(text) <= max_length:
        await bot.send_message(chat_id=chat_id, text=text)
    else:
        for i in range(0, len(text), max_length):
            chunk = text[i : i + max_length]
            await bot.send_message(chat_id=chat_id, text=chunk)


async def download_telegram_photo(photo_file) -> bytes:
    """Download a photo from Telegram.

    Args:
        photo_file: A telegram.File object obtained from photo.get_file()

    Returns:
        The image bytes.
    """
    byte_array = await photo_file.download_as_bytearray()
    return bytes(byte_array)
