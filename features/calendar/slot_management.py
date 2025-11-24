import logging
import datetime
from .google_calendar_service import GoogleCalendarService

logger = logging.getLogger(__name__)

class SlotManagementHandler:
    def __init__(self):
        self.calendar_service = GoogleCalendarService()

    async def handle_schedule_command(self, update, context):
        chat_id = update.effective_chat.id
        logger.info(f"Received /schedule command from user {update.effective_user.id}")

        events = self.calendar_service.get_upcoming_events()

        if not events:
            await context.bot.send_message(chat_id=chat_id, text="You have no upcoming events.")
            return

        message = "🗓️ Your upcoming schedule:\n\n"
        for event in events:
            summary = event['summary']
            start = event['start'].get('dateTime', event['start'].get('date'))
            
            try:
                start_dt = datetime.datetime.fromisoformat(start)
                # Format for display, assuming the service's timezone
                start_formatted = start_dt.strftime('%Y-%m-%d %H:%M')
                message += f"• *{summary}* at {start_formatted}\n"
            except ValueError:
                message += f"• *{summary}* on {start} (all-day)\n"

        await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')