import os
from dotenv import load_dotenv
from telegram.ext import CommandHandler, MessageHandler, filters
from features.calendar.event_creation import EventCreationHandler
from features.calendar.slot_management import SlotManagementHandler
from features.voice.transcription import transcribe_voice
from utils.logger import setup_logging
from telegram_bot import TelegramBot

async def voice_processing_middleware(update, context):
    """
    Middleware to intercept voice messages, transcribe them, and populate message.text
    so that downstream handlers (like event creation) can process them as text.
    """
    if update.message and update.message.voice:
        await update.message.reply_text("Listening... 👂")
        text = await transcribe_voice(update)
        if text:
            # Modify the update object in-place
            update.message.text = text
            await update.message.reply_text(f"I heard: \"{text}\"")
        else:
            await update.message.reply_text("Sorry, I couldn't understand the audio.")

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

    # Voice Middleware (Group -1 to run before other handlers)
    bot.application.add_handler(MessageHandler(filters.VOICE, voice_processing_middleware), group=-1)

    # Get the conversation handler for event creation
    event_conv_handler = event_creation_handler.get_conversation_handler()

    # Register handlers
    bot.application.add_handler(event_conv_handler)
    bot.application.add_handler(CommandHandler("schedule", slot_management_handler.handle_schedule_command))

    # Start the bot
    bot.run()

if __name__ == '__main__':
    main()
