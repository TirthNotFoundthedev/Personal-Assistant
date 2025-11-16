import datetime
import logging
from telegram import Update
from features.calendar.event_parser import EventParser
from features.calendar.google_calendar_service import GoogleCalendarService

logger = logging.getLogger(__name__)

class CalendarHandler:
    def __init__(self):
        self.calendar_service = GoogleCalendarService()
        self.event_parser = EventParser(self.calendar_service)
        logger.info("CalendarHandler initialized.")

    async def handle_calendar_message(self, update: Update, context):
        """
        Handles messages related to calendar events.
        Parses the message, creates calendar events, and sends a confirmation.
        """
        user_message = update.message.text
        chat_id = update.effective_chat.id
        logger.info(f"Received calendar message from user {update.effective_user.id}: '{user_message}'")

        event_list = self.event_parser.parse_event_from_text(user_message)
        
        if not event_list:
            logger.info("No event details extracted from message.")
            await context.bot.send_message(chat_id=chat_id, text="🤔 I couldn't extract any event details from your message. Please try again with more context.")
            return

        confirmation_messages = []
        for event_data in event_list:
            if event_data and event_data.get("title"):
                title = event_data["title"]
                date_str = event_data.get("date")
                start_time_str = event_data.get("start_time")
                end_time_str = event_data.get("end_time")

                try:
                    if not all([date_str, start_time_str, end_time_str]):
                        raise ValueError("Incomplete date/time information from parser.")
                    
                    start_datetime = datetime.datetime.strptime(f"{date_str} {start_time_str}", "%Y-%m-%d %H:%M:%S")
                    end_datetime = datetime.datetime.strptime(f"{date_str} {end_time_str}", "%Y-%m-%d %H:%M:%S")
                    
                    if end_datetime < start_datetime:
                        end_datetime += datetime.timedelta(days=1)

                    target_calendar_id = event_data.get("calendar_id", "primary")
                    
                    event = self.calendar_service.create_event(
                        summary=title,
                        start_datetime=start_datetime,
                        end_datetime=end_datetime,
                        description=user_message,
                        calendar_id=target_calendar_id
                    )

                    if event:
                        confirmation_messages.append(f"✅ Event '{title}' created.")
                    else:
                        confirmation_messages.append(f"❌ Failed to create event '{title}'.")

                except (ValueError, TypeError) as e:
                    logger.error(f"Error processing event data for '{title}': {e}", exc_info=True)
                    confirmation_messages.append(f"🤔 Could not process event '{title}' due to invalid data.")
                    continue
            else:
                logger.warning(f"Invalid event data received: {event_data}")

        if confirmation_messages:
            final_message = "\n".join(confirmation_messages)
            await context.bot.send_message(chat_id=chat_id, text=final_message)
        else:
            await context.bot.send_message(chat_id=chat_id, text="❌ No events were created from your message.")

    async def handle_show_events_message(self, update: Update, context):
        """
        Fetches and displays upcoming calendar events to the user.
        """
        chat_id = update.effective_chat.id
        logger.info(f"Received request to show events from user {update.effective_user.id}")

        events = self.calendar_service.get_upcoming_events()

        if not events:
            message = "🗓️ No upcoming events found."
        else:
            message = "🗓️ Your upcoming events:\n\n"
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                summary = event['summary']
                start_dt = datetime.datetime.fromisoformat(start.replace("Z", "+00:00"))
                
                message += f"• *{summary}* on {start_dt.strftime('%Y-%m-%d at %H:%M')}\n"
        
        await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')