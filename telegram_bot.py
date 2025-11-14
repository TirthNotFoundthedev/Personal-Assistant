import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler
import logging

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        load_dotenv()
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            logger.error("TELEGRAM_BOT_TOKEN not found in .env file")
            raise ValueError("TELEGRAM_BOT_TOKEN not found in .env file")
        
        self.application = Application.builder().token(self.token).build()
        logger.info("TelegramBot initialized.")

        # Register handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        logger.info("Telegram /start command handler registered.")

    async def start_command(self, update: Update, context):
        """Sends a welcome message when the command /start is issued."""
        logger.info(f"Received /start command from user {update.effective_user.id}")
        await update.message.reply_text("Hello! I'm your Personal Assistant bot. How can I help you today?")

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
    bot = TelegramBot()
    bot.run()
