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
from features.google_calendar_service import GoogleCalendarService

logger = logging.getLogger(__name__)

# Conversation states
SELECTING_CALENDAR = range(1)

class EventCreationHandler:
    def __init__(self):
        self.calendar_service = GoogleCalendarService()
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found in .env file")
        # Lazy initialization of the model
        self._model = None

    @property
    def model(self):
        if self._model is None:
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_api_key)
            self._model = genai.GenerativeModel('gemini-flash-latest')
        return self._model

    def _parse_events_from_text(self, text: str) -> list:
        current_date = datetime.date.today().isoformat()
        prompt = f"""
        Today's date is {current_date}.
        Extract all event details (title, date, start time, and end time) from the text.
        Resolve relative dates (e.g., "tomorrow") to absolute dates (YYYY-MM-DD).
        Resolve times to HH:MM:SS format.
        If an end time is not specified, assume the event is 1 hour long.
        Return the output as a JSON array of objects, each with 'title', 'date', 'start_time', and 'end_time'.
        If no events are found, return an empty array [].

        Text: "{text}"
        """
        try:
            response = self.model.generate_content(prompt)
            json_output = response.text.strip().replace("```json", "").replace("```", "").strip()
            return json.loads(json_output)
        except Exception as e:
            logger.error(f"Error parsing events with Gemini: {e}")
            return []

    async def handle_message_entry_point(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Starts the event creation conversation."""
        user_message = update.message.text
        parsed_events = self._parse_events_from_text(user_message)

        if not parsed_events:
            await update.message.reply_text("I couldn't find any event details in your message.")
            return ConversationHandler.END

        context.user_data['events_to_create'] = parsed_events
        context.user_data['current_event_index'] = 0

        await self._ask_for_calendar(update.effective_chat.id, context)
        return SELECTING_CALENDAR

    async def _ask_for_calendar(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Sends a message asking the user to select a calendar for the current event."""
        event_index = context.user_data['current_event_index']
        event_data = context.user_data['events_to_create'][event_index]
        event_title = event_data.get('title', 'this event')

        calendars = self.calendar_service.get_writable_calendars()
        if not calendars:
            await context.bot.send_message(chat_id=chat_id, text="I couldn't find any calendars you've given me access to.")
            return ConversationHandler.END
        
        context.user_data['writable_calendars'] = calendars

        keyboard = [[InlineKeyboardButton(c['summary'], callback_data=str(i))] for i, c in enumerate(calendars)]
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

        calendar_id = calendars[calendar_index]['id']
        event_index = context.user_data['current_event_index']
        event_data = context.user_data['events_to_create'][event_index]
        
        try:
            title = event_data['title']
            start_datetime = datetime.datetime.fromisoformat(f"{event_data['date']}T{event_data['start_time']}")
            end_datetime = datetime.datetime.fromisoformat(f"{event_data['date']}T{event_data['end_time']}")
            
            event = self.calendar_service.create_event(title, start_datetime, end_datetime, calendar_id)
            if event:
                await query.edit_message_text(text=f"✅ Event '{title}' created successfully!")
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

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancels and ends the conversation."""
        await update.message.reply_text('Operation cancelled.')
        context.user_data.clear()
        return ConversationHandler.END

    def get_conversation_handler(self) -> ConversationHandler:
        """Returns the conversation handler for event creation."""
        return ConversationHandler(
            entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message_entry_point)],
            states={
                SELECTING_CALENDAR: [CallbackQueryHandler(self.handle_calendar_selection)],
            },
            fallbacks=[],
        )