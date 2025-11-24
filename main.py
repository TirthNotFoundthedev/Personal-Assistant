import os
from dotenv import load_dotenv
from telegram.ext import CommandHandler
from features.calendar.event_creation import EventCreationHandler
from features.calendar.slot_management import SlotManagementHandler
from utils.logger import setup_logging
from telegram_bot import TelegramBot

def main():
    # Initialize logging first
    setup_logging()

    # Load environment variables from .env file
    load_dotenv()

    # Initialize Telegram Bot
    bot = TelegramBot()

    # Initialize new handlers
    event_creation_handler = EventCreationHandler()
    slot_management_handler = SlotManagementHandler()

    # Get the conversation handler for event creation
    event_conv_handler = event_creation_handler.get_conversation_handler()

    # Register handlers
    bot.application.add_handler(event_conv_handler)
    bot.application.add_handler(CommandHandler("schedule", slot_management_handler.handle_schedule_command))

    # Start the bot
    bot.run()

if __name__ == '__main__':
    main()
