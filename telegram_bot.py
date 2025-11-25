import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import logging
import google.generativeai as genai
import tempfile
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
        self.model = genai.GenerativeModel("gemini-2.5-flash")

        self.application = Application.builder().token(self.token).build()
        logger.info("TelegramBot initialized.")

        # Register handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(MessageHandler(filters.VOICE, self.handle_voice))
        logger.info("Telegram command and voice handlers registered.")

    async def start_command(self, update: Update, context):
        """Sends a welcome message when the command /start is issued."""
        logger.info(f"Received /start command from user {update.effective_user.id}")
        await update.message.reply_text("Hello! I'm your Personal Assistant bot. Send me a voice message and I'll listen!")

    async def handle_voice(self, update: Update, context):
        """Handles voice messages by transcribing and processing them with Gemini."""
        user_id = update.effective_user.id
        logger.info(f"Received voice message from user {user_id}")
        
        try:
            # Get the voice file
            voice_file = await update.message.voice.get_file()
            
            # Create a temporary file to save the voice message
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_voice:
                temp_voice_path = temp_voice.name
            
            await voice_file.download_to_drive(custom_path=temp_voice_path)
            logger.info(f"Voice file downloaded to {temp_voice_path}")

            # Upload to Gemini
            # Note: For very short clips, we might be able to pass bytes directly if supported, 
            # but file upload is safer for general audio.
            # Gemini 1.5 Flash supports audio input.
            
            # We need to send the audio to the model.
            # Currently, the best way for audio with the python client is often uploading the file.
            
            uploaded_file = genai.upload_file(path=temp_voice_path)
            
            # Generate content
            # We can prompt the model to act as a personal assistant responding to the audio.
            response = self.model.generate_content(
                [
                    "Listen to this audio and respond as a helpful personal assistant. If it's a command, confirm it. If it's a question, answer it.",
                    uploaded_file
                ]
            )
            
            response_text = response.text
            logger.info(f"Gemini response: {response_text}")
            
            await update.message.reply_text(response_text)

        except Exception as e:
            logger.error(f"Error handling voice message: {e}", exc_info=True)
            await update.message.reply_text("Sorry, I had trouble processing your voice message.")
        
        finally:
            # Cleanup
            if 'temp_voice_path' in locals() and os.path.exists(temp_voice_path):
                os.remove(temp_voice_path)
                logger.info(f"Deleted temporary file {temp_voice_path}")

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
