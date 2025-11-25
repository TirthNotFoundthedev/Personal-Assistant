import os
import tempfile
import logging
import google.generativeai as genai
from telegram import Update

logger = logging.getLogger(__name__)

async def transcribe_voice(update: Update) -> str:
    """
    Downloads the voice file from the update, uploads it to Gemini,
    and returns the transcribed text.
    """
    voice_file = await update.message.voice.get_file()
    
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_voice:
        temp_voice_path = temp_voice.name
    
    try:
        await voice_file.download_to_drive(custom_path=temp_voice_path)
        logger.info(f"Voice file downloaded to {temp_voice_path}")

        # Ensure Gemini is configured (it might be configured in main, but good to be safe or assume it is)
        # For now, we assume genai.configure was called in main or the caller.
        
        # Using gemini-2.5-flash as per previous fix
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        uploaded_file = genai.upload_file(path=temp_voice_path)
        
        response = model.generate_content(
            [
                "Transcribe the following audio file exactly. Output only the transcribed text, no other commentary.",
                uploaded_file
            ]
        )
        
        transcript = response.text.strip()
        logger.info(f"Transcribed text: {transcript}")
        return transcript

    except Exception as e:
        logger.error(f"Error transcribing voice: {e}", exc_info=True)
        return ""
        
    finally:
        if 'temp_voice_path' in locals() and os.path.exists(temp_voice_path):
            os.remove(temp_voice_path)
