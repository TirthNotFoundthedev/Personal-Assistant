import os
from dotenv import load_dotenv
from telegram.ext import MessageHandler, filters, CommandHandler
from telegram_bot import TelegramBot
from features.calendar.calendar_handler import CalendarHandler
from utils.logger import setup_logging # Import the setup_logging function

def main():
    # Initialize logging first
    setup_logging()

    # Load environment variables from .env file
    load_dotenv()

    # Initialize Telegram Bot
    bot = TelegramBot()

    # Initialize Calendar Handler
    calendar_handler = CalendarHandler()

    # Register Calendar Handler for text messages
    bot.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, calendar_handler.handle_calendar_message))

    # Register command handler for showing events
    bot.application.add_handler(CommandHandler("showevents", calendar_handler.handle_show_events_message))

    # Start the bot
    bot.run()

if __name__ == '__main__':
    main()
