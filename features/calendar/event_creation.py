import datetime
import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from .google_calendar_service import GoogleCalendarService
from utils.event_logger import log_event_creation
from features.calendar.AIs.Categorisation_AI.predictor import CategorizationPredictor

logger = logging.getLogger(__name__)

# Conversation states
SELECTING_CALENDAR = range(1)
class EventCreationHandler:
    def __init__(self):
        self.calendar_service = GoogleCalendarService()
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found in .env file")
        # Lazy initialization of the Gemini model
        self._gemini_model = None
        self.custom_ai_predictor = CategorizationPredictor() # Initialize custom AI predictor

    @property
    def gemini_model(self):
        if self._gemini_model is None:
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_api_key)
            self._gemini_model = genai.GenerativeModel('gemini-flash-latest')
        return self._gemini_model

    def _parse_events_from_text(self, text: str, calendars: list) -> list:
        current_date = datetime.date.today().isoformat()
        
        # Use provided calendars to provide context to the model
        calendar_info = "\n".join([
            f"- ID: {c['id']}, Name: {c['summary']}" 
            for c in calendars
        ])

        prompt = f"""
        Today's date is {current_date}.
        You are an intelligent assistant that extracts event details from text and suggests an appropriate calendar.

        Available Calendars:
        {calendar_info}

        From the text below, extract all events. For each event, provide:
        1. 'title': A concise title for the event.
        2. 'date': The event's date in YYYY-MM-DD format.
        3. 'start_time': The event's start time in HH:MM:SS format.
        4. 'end_time': The event's end time in HH:MM:SS format. If not specified, assume a 1-hour duration.
        5. 'suggested_calendar_id': The ID of the most appropriate calendar from the list above.

        Return the output as a JSON array of objects. If no events are found, return an empty array [].

        Text: "{text}"
        """
        try:
            response = self.gemini_model.generate_content(prompt)
            json_output = response.text.strip().replace("```json", "").replace("```", "").strip()
            logger.debug(f"Gemini API raw response: {json_output}")
            
            parsed_events = json.loads(json_output)
            logger.debug(f"Parsed events from Gemini (before custom AI): {parsed_events}")

            # Add custom AI prediction
            for event in parsed_events:
                custom_ai_predicted_name = self.custom_ai_predictor.predict(event.get('title', text))
                if custom_ai_predicted_name:
                    # Find the corresponding calendar ID from the writable calendars
                    for cal in calendars:
                        if cal['summary'] == custom_ai_predicted_name:
                            event['custom_ai_suggested_calendar_id'] = cal['id']
                            break
            
            return parsed_events
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding error from Gemini response: {e}. Raw response: '{json_output}'")
            return []
        except Exception as e:
            logger.error(f"Error parsing events with Gemini: {e}", exc_info=True)
            return []

    async def handle_message_entry_point(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Starts the event creation conversation."""
        user_message = update.message.text

        # Fetch calendars once and cache them
        calendars = self.calendar_service.get_writable_calendars()
        context.user_data['writable_calendars'] = calendars

        parsed_events = self._parse_events_from_text(user_message, calendars)
        logger.debug(f"Parsed events after Gemini and custom AI: {parsed_events}")

        if not parsed_events:
            await update.message.reply_text("I couldn't find any event details in your message.")
            return ConversationHandler.END

        context.user_data['original_message'] = user_message
        context.user_data['events_to_create'] = parsed_events
        context.user_data['current_event_index'] = 0

        await self._ask_for_calendar(update.effective_chat.id, context)
        return SELECTING_CALENDAR

    async def _ask_for_calendar(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Sends a message asking the user to select a calendar for the current event."""
        event_index = context.user_data['current_event_index']
        event_data = context.user_data['events_to_create'][event_index]
        event_title = event_data.get('title', 'this event')
        gemini_suggested_id = event_data.get('suggested_calendar_id')
        custom_ai_suggested_id = event_data.get('custom_ai_suggested_calendar_id')
        logger.debug(f"Gemini suggested ID: {gemini_suggested_id}, Custom AI suggested ID: {custom_ai_suggested_id}")

        calendars = context.user_data.get('writable_calendars', [])
        if not calendars:
            await context.bot.send_message(chat_id=chat_id, text="I couldn't find any calendars you've given me access to.")
            return ConversationHandler.END
        
        # context.user_data['writable_calendars'] = calendars # Already set in entry point

        keyboard = []
        for i, calendar in enumerate(calendars):
            button_text = calendar['summary']
            if calendar['id'] == gemini_suggested_id:
                button_text += " 🤖"  # Add an indicator for Gemini's suggestion
            if calendar['id'] == custom_ai_suggested_id:
                button_text += " 🧠" # Add an indicator for Custom AI's suggestion
            keyboard.append([InlineKeyboardButton(button_text, callback_data=str(i))])
        
        # Add Skip and Cancel buttons
        keyboard.append([
            InlineKeyboardButton("⏩ Skip Event", callback_data='skip_event'),
            InlineKeyboardButton("❌ Cancel All", callback_data='cancel_all')
        ])
        
        logger.debug(f"Generated keyboard: {keyboard}")
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Which calendar should I add '{event_title}' to?",
            reply_markup=reply_markup
        )

    async def handle_calendar_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handles the user's calendar selection, creates the event, and continues to the next event if any."""
        query = update.callback_query
        await query.answer()
        
        calendar_index = int(query.data)
        calendars = context.user_data.get('writable_calendars', [])
        
        if not (0 <= calendar_index < len(calendars)):
            await query.edit_message_text(text="Invalid selection. Please try again.")
            return ConversationHandler.END

        selected_calendar = calendars[calendar_index]
        calendar_id = selected_calendar['id']
        calendar_name = selected_calendar['summary']

        event_index = context.user_data['current_event_index']
        event_data = context.user_data['events_to_create'][event_index]
        original_message = context.user_data.get('original_message', '')
        
        try:
            title = event_data['title']
            start_datetime = datetime.datetime.fromisoformat(f"{event_data['date']}T{event_data['start_time']}")
            end_datetime = datetime.datetime.fromisoformat(f"{event_data['date']}T{event_data['end_time']}")
            
            event = self.calendar_service.create_event(title, start_datetime, end_datetime, calendar_id)
            if event:
                await query.edit_message_text(text=f"✅ Event '{title}' created in '{calendar_name}' calendar.")
                # Log the successful event creation
                log_event_creation(
                    original_message=title, # Use title to match backfill data and prediction logic
                    event_title=title,
                    calendar_name=calendar_name
                )
            else:
                await query.edit_message_text(text=f"❌ Failed to create event '{title}'.")
        except (KeyError, ValueError) as e:
            logger.error(f"Error processing event data {event_data}: {e}")
            await query.edit_message_text(text="❌ Error processing this event.")

        context.user_data['current_event_index'] += 1
        if context.user_data['current_event_index'] < len(context.user_data['events_to_create']):
            await self._ask_for_calendar(update.effective_chat.id, context)
            return SELECTING_CALENDAR
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="All events processed.")
            context.user_data.clear()
            return ConversationHandler.END

    async def _handle_skip_event(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()
        event_index = context.user_data['current_event_index']
        event_data = context.user_data['events_to_create'][event_index]
        event_title = event_data.get('title', 'this event')
        await query.edit_message_text(text=f"⏩ Skipped event '{event_title}'.")

        context.user_data['current_event_index'] += 1
        if context.user_data['current_event_index'] < len(context.user_data['events_to_create']):
            await self._ask_for_calendar(update.effective_chat.id, context)
            return SELECTING_CALENDAR
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="All events processed.")
            context.user_data.clear()
            return ConversationHandler.END

    async def _handle_cancel_all(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text="❌ Event creation cancelled.")
        context.user_data.clear()
        return ConversationHandler.END

    def get_conversation_handler(self) -> ConversationHandler:
        """Returns the conversation handler for event creation."""
        return ConversationHandler(
            entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message_entry_point)],
            states={
                SELECTING_CALENDAR: [
                    CallbackQueryHandler(self.handle_calendar_selection, pattern=r'^\d+$'), # Handles numeric calendar selection
                    CallbackQueryHandler(self._handle_skip_event, pattern='^skip_event$'),
                    CallbackQueryHandler(self._handle_cancel_all, pattern='^cancel_all$'),
                ],
            },
            fallbacks=[],
        )