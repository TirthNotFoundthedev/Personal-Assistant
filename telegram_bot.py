import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler
import logging
import google.generativeai as genai
import pathlib

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        load_dotenv()
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            logger.error("TELEGRAM_BOT_TOKEN not found in .env file")
            raise ValueError("TELEGRAM_BOT_TOKEN not found in .env file")
        
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not self.gemini_api_key:
             logger.error("GEMINI_API_KEY not found in .env file")
             raise ValueError("GEMINI_API_KEY not found in .env file")
        
        genai.configure(api_key=self.gemini_api_key)
        # self.model = genai.GenerativeModel("gemini-2.5-flash") # Model initialization moved to features

        self.application = Application.builder().token(self.token).build()
        logger.info("TelegramBot initialized.")

        # Register handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        # Voice handler is now registered in main.py to allow interaction with other features
        logger.info("Telegram /start command handler registered.")

    async def start_command(self, update: Update, context):
        """Sends a welcome message when the command /start is issued."""
        logger.info(f"Received /start command from user {update.effective_user.id}")
        await update.message.reply_text("Hello! I'm your Personal Assistant bot. Send me a voice message and I'll listen!")

    def run(self):
        """Starts the bot."""
        logger.info("Bot started polling...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("Bot stopped polling.")


if __name__ == '__main__':
    # This block is for direct testing of telegram_bot.py,
    # but main.py will be the primary entry point.
    # Ensure logging is set up if running this directly for testing.
    # from utils.logger import setup_logging
    # setup_logging()
    # Note: We need to ensure .env is loaded if running directly, which __init__ does.
    try:
        bot = TelegramBot()
        bot.run()
    except Exception as e:
        print(f"Failed to start bot: {e}")
