import datetime
import logging
import os
import sys

from features.calendar.google_calendar_service import GoogleCalendarService
from utils.event_logger import log_event_creation, setup_event_logger
from utils.logger import setup_logging # Assuming setup_logging is in utils.logger

# Setup logging for this script
setup_logging()
logger = logging.getLogger(__name__)

def backfill_events(years_back: int = 3):
    """
    Fetches past events from Google Calendar and logs them to event_log.csv.
    :param years_back: How many years back from today to fetch events.
    """
    logger.info(f"Starting backfill of events for the last {years_back} years.")
    
    calendar_service = GoogleCalendarService()
    setup_event_logger() # Ensure CSV headers are present

    # Use get_writable_calendars to only process calendars where events can be added
    all_calendars = calendar_service.get_writable_calendars()
    if not all_calendars:
        logger.error("No writable calendars found. Exiting backfill.")
        return

    # Create a mapping from calendar ID to calendar summary (name)
    calendar_id_to_name = {cal['id']: cal['summary'] for cal in all_calendars}

    end_date = datetime.datetime.now(calendar_service.timezone)
    start_date = end_date - datetime.timedelta(days=years_back * 365) # Approximate years

    total_logged_events = 0

    for calendar in all_calendars:
        cal_id = calendar['id']
        cal_name = calendar['summary']
        logger.info(f"Fetching events for calendar: '{cal_name}' (ID: {cal_id})")

        events = calendar_service.get_events_in_range(cal_id, start_date, end_date)
        
        if not events:
            logger.info(f"No events found for calendar '{cal_name}' in the specified range.")
            continue

        for event in events:
            event_summary = event.get('summary', 'No Title')
            
            # Log event creation. For backfill, original_message is the event summary.
            log_event_creation(
                original_message=event_summary,
                event_title=event_summary,
                calendar_name=cal_name
            )
            total_logged_events += 1
            logger.debug(f"Logged event: '{event_summary}' in '{cal_name}'")
    
    logger.info(f"Backfill complete. Total events logged: {total_logged_events}")

if __name__ == '__main__':
    # You can change the number of years to backfill here
    backfill_events(years_back=3)
