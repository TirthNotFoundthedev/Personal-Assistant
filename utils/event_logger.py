import csv
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LOG_FILE = os.path.join(BASE_DIR, 'features', 'calendar', 'AIs', 'Categorisation_AI', 'event_data.csv')
HEADERS = ['timestamp', 'original_user_message', 'event_title', 'user_selected_calendar_name']

def setup_event_logger():
    """Create the CSV file and write the header if it doesn't exist."""
    if not os.path.exists(LOG_FILE):
        try:
            os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
            with open(LOG_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(HEADERS)
        except IOError as e:
            logger.error(f"Failed to create or write to event log file: {e}")

def log_event_creation(original_message: str, event_title: str, calendar_name: str):
    """Append a new event record to the CSV log."""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'original_user_message': original_message,
        'event_title': event_title,
        'user_selected_calendar_name': calendar_name,
    }
    try:
        with open(LOG_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=HEADERS)
            writer.writerow(log_entry)
    except IOError as e:
        logger.error(f"Failed to write to event log file: {e}")

# Ensure the logger is set up when the module is imported
setup_event_logger()
