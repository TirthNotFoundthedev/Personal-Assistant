import os
import logging
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import google.generativeai as gemini
import tempfile
import io
import json # ADDED THIS IMPORT

from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from features.toggle import toggl_api # Import the toggl_api module

# Load environment variables from .env file
load_dotenv()

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Gemini
if GEMINI_API_KEY:
    gemini.configure(api_key=GEMINI_API_KEY)
    gemini_model = gemini.GenerativeModel('gemini-1.5-flash') # Using a free model
else:
    logger.warning("GEMINI_API_KEY not set. Gemini features will be disabled.")
    gemini_model = None

app = Flask(__name__)

# Initialize Telegram Bot and Dispatcher
bot = Bot(TELEGRAM_BOT_TOKEN)
dispatcher = Dispatcher(bot, None)

# --- Gemini Functions ---
def transcribe_audio(audio_bytes: bytes) -> str:
    """Transcribes audio using the Gemini model."""
    if not gemini_model:
        raise ValueError("Gemini model not initialized. GEMINI_API_KEY might be missing.")
    
    # Gemini's `generate_content` expects file-like objects for audio input
    audio_file = {'mime_type': 'audio/ogg', 'data': io.BytesIO(audio_bytes)}
    response = gemini_model.generate_content([audio_file])
    return response.text

GEMINI_INTENT_SYSTEM_PROMPT = """
You are an intent recognition system for a personal assistant bot.
Your task is to analyze user messages and extract their intent, specifically for Toggl time tracking.
Respond only with a JSON object containing the 'action', 'description', and 'duration_seconds' (if applicable).
If no clear Toggl-related intent is found, return "action": "none".

Actions can be: "start_timer", "add_entry", "stop_timer", "get_status".

Examples:
User: "Start a timer for coding"
Response: {"action": "start_timer", "description": "coding"}

User: "Add 30 minutes for meeting prep"
Response: {"action": "add_entry", "description": "meeting prep", "duration_seconds": 1800}

User: "Stop current task"
Response: {"action": "stop_timer"}

User: "What am I working on?"
Response: {"action": "get_status"}

User: "Remind me in 5 minutes"
Response: {"action": "none"}

User: "Start 'reading documentation' for 1 hour"
Response: {"action": "start_timer", "description": "reading documentation", "duration_seconds": 3600}
"""

def get_gemini_intent(text: str) -> dict:
    """Uses Gemini to determine the user's intent for Toggl actions."""
    if not gemini_model:
        logger.warning("Gemini model not initialized for intent detection.")
        return {"action": "none", "raw_text": text}

    try:
        response = gemini_model.generate_content([
            GEMINI_INTENT_SYSTEM_PROMPT,
            f"User: {text}\nResponse: "
        ])
        # Gemini often wraps JSON in markdown, so we need to extract it
        response_text = response.text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        intent = json.loads(response_text)
        intent['raw_text'] = text # Store original text for context
        return intent
    except Exception as e:
        logger.error(f"Error getting Gemini intent for text '{text}': {e}")
        return {"action": "none", "raw_text": text, "error": str(e)}


# --- Telegram Bot Handlers ---
def start(update: Update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi! I am your Personal Assistant Bot. How can I help you today?')

def handle_text_message(update: Update, context):
    """Handles incoming text messages, processes them with Gemini NLU and performs Toggl actions."""
    user_text = update.message.text
    if not gemini_model:
        update.message.reply_text(f"Gemini features are disabled. Please provide a GEMINI_API_KEY to enable smart processing.")
        return
    
    intent = get_gemini_intent(user_text)
    context.user_data['last_intent'] = intent # Store original text for context

    action = intent.get("action")
    description = intent.get("description", user_text) # Use original text as description if none from Gemini
    duration_seconds = intent.get("duration_seconds")
    project_id = context.user_data.get('selected_project_id')

    try:
        if action == "start_timer":
            if not project_id:
                update.message.reply_text("Please select a project first using /toggl_clients.")
                return
            
            toggl_api.start_time_entry(description=description, project_id=project_id)
            update.message.reply_text(f"Started Toggl timer for '{description}' on project ID {project_id}.")

        elif action == "add_entry":
            if not project_id:
                update.message.reply_text("Please select a project first using /toggl_clients.")
                return
            if not duration_seconds:
                update.message.reply_text("I need a duration to add a time entry. E.g., 'add 30 minutes for meeting'.")
                return
            
            toggl_api.create_time_entry(description=description, duration_seconds=duration_seconds, project_id=project_id)
            update.message.reply_text(f"Added Toggl entry for '{description}' ({duration_seconds/60} minutes) on project ID {project_id}.")

        elif action == "stop_timer":
            stopped_entry = toggl_api.stop_active_time_entry()
            if stopped_entry:
                update.message.reply_text(f"Stopped active Toggl timer: '{stopped_entry.get('description', 'No description')}'.")
            else:
                update.message.reply_text("No active Toggl timer found to stop.")

        elif action == "get_status":
            update.message.reply_text("Toggl status check is not yet fully implemented. I can tell you if a timer is running here.") # To be expanded later
            
        elif action == "none":
            update.message.reply_text(f"I'm not sure how to handle that. Detected intent: {json.dumps(intent, indent=2)}")
        
        else:
            update.message.reply_text(f"Unknown action: {action}. Detected intent: {json.dumps(intent, indent=2)}")

    except ValueError as ve:
        update.message.reply_text(f"Toggl API Error: {ve}. Please ensure your TOGGL_API_KEY is correct.")
    except Exception as e:
        logger.error(f"Error processing Toggl action for text '{user_text}': {e}")
        update.message.reply_text(f"An error occurred while performing the Toggl action: {e}")

def error_handler(update: Update, context):
    """Log the error and send a telegram message to notify the developer."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)
    if update.effective_message:
        update.effective_message.reply_text(f'An error occurred: {context.error}')

def toggl_clients_command(update: Update, context):
    """Fetches Toggl clients and presents them as inline buttons."""
    try:
        clients = toggl_api.get_clients()
        if not clients:
            update.message.reply_text("No Toggl clients found.")
            return

        keyboard = []
        for client in clients:
            keyboard.append([InlineKeyboardButton(client['name'], callback_data=f"client_{client['id']}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text('Please choose a client:', reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error fetching Toggl clients: {e}")
        update.message.reply_text(f"Failed to fetch clients. Error: {e}")

def button_handler(update: Update, context):
    """Handles callback queries from inline keyboard buttons."""
    query = update.callback_query
    query.answer() # Acknowledge the query

    data = query.data
    chat_id = query.message.chat_id
    message_id = query.message.message_id

    if data.startswith("client_"):
        client_id = int(data.split("_")[1])
        context.user_data['selected_client_id'] = client_id
        
        try:
            projects = toggl_api.get_projects(client_id)
            if not projects:
                query.edit_message_text(f"No projects found for the selected client.")
                return

            keyboard = []
            for project in projects:
                keyboard.append([InlineKeyboardButton(project['name'], callback_data=f"project_{project['id']}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.edit_message_text('Please choose a project:', reply_markup=reply_markup)
        
        except Exception as e:
            logger.error(f"Error fetching Toggl projects for client {client_id}: {e}")
            query.edit_message_text(f"Failed to fetch projects. Error: {e}")

    elif data.startswith("project_"):
        project_id = int(data.split("_")[1])
        context.user_data['selected_project_id'] = project_id
        
        query.edit_message_text(f"Project selected: {project_id}. Now you can start a timer or add an entry.")
        # Here you might want to ask for description or immediately start/add a timer.
        # For now, just confirm selection.

def voice_message_handler(update: Update, context):
    """Handles incoming voice messages, transcribes them using Gemini, and echoes the text."""
    if not gemini_model:
        update.message.reply_text("Gemini features are disabled. GEMINI_API_KEY might be missing.")
        return

    update.message.reply_text("Processing your voice message...")
    try:
        # Get the file_id of the voice message
        voice_file = bot.get_file(update.message.voice.file_id)
        
        # Download the file content
        audio_bytes = voice_file.download_as_bytearray()
        
        # Transcribe using Gemini
        transcribed_text = transcribe_audio(bytes(audio_bytes))
        
        update.message.reply_text(f"Transcription: {transcribed_text}")
        
        intent = get_gemini_intent(transcribed_text)
        context.user_data['last_transcription'] = transcribed_text
        context.user_data['last_intent'] = intent

        action = intent.get("action")
        description = intent.get("description", transcribed_text)
        duration_seconds = intent.get("duration_seconds")
        project_id = context.user_data.get('selected_project_id')

        try:
            if action == "start_timer":
                if not project_id:
                    update.message.reply_text("Please select a project first using /toggl_clients.")
                    return
                
                toggl_api.start_time_entry(description=description, project_id=project_id)
                update.message.reply_text(f"Started Toggl timer for '{description}' on project ID {project_id}.")

            elif action == "add_entry":
                if not project_id:
                    update.message.reply_text("Please select a project first using /toggl_clients.")
                    return
                if not duration_seconds:
                    update.message.reply_text("I need a duration to add a time entry. E.g., 'add 30 minutes for meeting'.")
                    return
                
                toggl_api.create_time_entry(description=description, duration_seconds=duration_seconds, project_id=project_id)
                update.message.reply_text(f"Added Toggl entry for '{description}' ({duration_seconds/60} minutes) on project ID {project_id}.")

            elif action == "stop_timer":
                stopped_entry = toggl_api.stop_active_time_entry()
                if stopped_entry:
                    update.message.reply_text(f"Stopped active Toggl timer: '{stopped_entry.get('description', 'No description')}'.")
                else:
                    update.message.reply_text("No active Toggl timer found to stop.")

            elif action == "get_status":
                update.message.reply_text("Toggl status check is not yet fully implemented. I can tell you if a timer is running here.") # To be expanded later
                
            elif action == "none":
                update.message.reply_text(f"I'm not sure how to handle that. Detected intent: {json.dumps(intent, indent=2)}")
            
            else:
                update.message.reply_text(f"Unknown action: {action}. Detected intent: {json.dumps(intent, indent=2)}")

        except ValueError as ve:
            update.message.reply_text(f"Toggl API Error: {ve}. Please ensure your TOGGL_API_KEY is correct.")
        except Exception as e:
            logger.error(f"Error processing Toggl action for voice message '{transcribed_text}': {e}")
            update.message.reply_text(f"An error occurred while performing the Toggl action: {e}")
    except Exception as e:
        logger.error(f"Error processing voice message: {e}")
        update.message.reply_text(f"Failed to process voice message. Error: {e}")

# --- Register Handlers to the Dispatcher ---
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("toggl_clients", toggl_clients_command))
dispatcher.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text_message))
dispatcher.add_handler(MessageHandler(filters.VOICE, voice_message_handler)) # New handler for voice messages
dispatcher.add_handler(CallbackQueryHandler(button_handler))
dispatcher.add_error_handler(error_handler)


# --- Flask Routes ---
@app.route('/')
def home():
    return "Personal Assistant Bot is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming Telegram updates."""
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), bot)
        dispatcher.process_update(update)
    return jsonify({"status": "success"}), 200

@app.route('/set_webhook', methods=['GET', 'POST'])
def set_telegram_webhook():
    """Sets the Telegram webhook URL."""
    if not WEBHOOK_URL:
        return jsonify({"status": "error", "message": "WEBHOOK_URL not set in .env"}), 500
    
    s = bot.setWebhook(WEBHOOK_URL)
    if s:
        return jsonify({"status": "success", "message": f"Webhook set to {WEBHOOK_URL}"}), 200
    else:
        return jsonify({"status": "error", "message": "Webhook setup failed"}), 500

if __name__ == '__main__':
    # Set the webhook on startup if WEBHOOK_URL is provided
    # and not running in development mode (e.g., FLASK_ENV=development)
    if TELEGRAM_BOT_TOKEN and WEBHOOK_URL and os.environ.get("FLASK_ENV") != "development":
        logger.info(f"Setting webhook to {WEBHOOK_URL}")
        try:
            bot.setWebhook(WEBHOOK_URL)
            logger.info("Webhook set successfully.")
        except Exception as e:
            logger.error(f"Failed to set webhook: {e}")
            
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
