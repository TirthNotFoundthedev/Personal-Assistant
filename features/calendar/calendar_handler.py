import datetime
from telegram import Update
from features.calendar.event_parser import EventParser
from features.calendar.google_calendar_service import GoogleCalendarService
import logging

logger = logging.getLogger(__name__)

class CalendarHandler:
    def __init__(self):
        self.event_parser = EventParser()
        self.calendar_service = GoogleCalendarService()
        logger.info("CalendarHandler initialized.")

    async def handle_calendar_message(self, update: Update, context):
        """
        Handles messages related to calendar events.
        Parses the message, creates a calendar event, and sends a confirmation.
        """
        user_message = update.message.text
        chat_id = update.effective_chat.id
        logger.info(f"Received calendar message from user {update.effective_user.id}: '{user_message}'")



        event_data = self.event_parser.parse_event_from_text(user_message)

        if event_data and event_data.get("title"):
            title = event_data["title"]
            date_str = event_data.get("date")
            start_time_str = event_data.get("start_time")
            end_time_str = event_data.get("end_time")
            logger.info(f"Parsed event data: Title='{title}', Date='{date_str}', StartTime='{start_time_str}', EndTime='{end_time_str}'")

            start_datetime = None
            end_datetime = None
            today = datetime.date.today()

            try:
                # Determine start_datetime
                if date_str and start_time_str:
                    start_datetime = datetime.datetime.strptime(f"{date_str} {start_time_str}", "%Y-%m-%d %H:%M:%S")
                elif date_str and not start_time_str: # Only date provided
                    start_datetime = datetime.datetime.strptime(date_str, "%Y-%m-%d").replace(hour=9, minute=0, second=0)
                elif not date_str and start_time_str: # Only start_time provided, assume today
                    start_datetime = datetime.datetime.strptime(f"{today.isoformat()} {start_time_str}", "%Y-%m-%d %H:%M:%S")
                else: # Only title, assume today 9 AM
                    start_datetime = datetime.datetime.combine(today, datetime.time(9, 0, 0))
                
                logger.debug(f"Resolved start_datetime: {start_datetime}")

                # Determine end_datetime
                if start_datetime:
                    if date_str and end_time_str:
                        # If end_time is provided, use it with the same date as start_datetime
                        end_datetime = datetime.datetime.strptime(f"{date_str} {end_time_str}", "%Y-%m-%d %H:%M:%S")
                        # Handle overnight events if end_time is earlier than start_time
                        if end_datetime < start_datetime:
                            end_datetime += datetime.timedelta(days=1)
                    elif not end_time_str:
                        # Default to 1 hour after start_datetime if no end_time is provided
                        end_datetime = start_datetime + datetime.timedelta(hours=1)
                
                logger.debug(f"Resolved end_datetime: {end_datetime}")

            except ValueError as e:
                logger.error(f"Error parsing date/time from event data: {e}. Data: Date='{date_str}', StartTime='{start_time_str}', EndTime='{end_time_str}'", exc_info=True)
                await context.bot.send_message(chat_id=chat_id, text="❌ Could not understand the date/time format. Please try again.")
                return

            if start_datetime and end_datetime:
                event = self.calendar_service.create_event(
                    summary=title,
                    start_datetime=start_datetime,
                    end_datetime=end_datetime,
                    description=user_message # Original message as description
                )

                if event:
                    confirmation_message = (
                        f"✅ Event '{title}' created for "
                        f"{start_datetime.strftime('%Y-%m-%d %H:%M')} "
                        f"to {end_datetime.strftime('%H:%M')}."
                    )
                    logger.info(f"Event creation successful. Sending confirmation: {confirmation_message}")
                    await context.bot.send_message(chat_id=chat_id, text=confirmation_message)
                else:
                    logger.error("Failed to create event in Google Calendar.")
                    await context.bot.send_message(chat_id=chat_id, text="❌ Failed to create event in Google Calendar. Check logs for details.")
            else:
                logger.warning("No valid start_datetime or end_datetime could be determined.")
                await context.bot.send_message(chat_id=chat_id, text="🤔 I couldn't determine a valid start and end time for the event. Please be more specific.")
        else:
            logger.info("No event details extracted from message.")
            await context.bot.send_message(chat_id=chat_id, text="🤔 I couldn't extract any event details from your message. Please try again with more context.")
