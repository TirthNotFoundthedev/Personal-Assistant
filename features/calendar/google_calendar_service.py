import os
import datetime
import pytz
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging
from dotenv import load_dotenv # Import load_dotenv

logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

class GoogleCalendarService:
    def __init__(self, credentials_path='client_secret.json', token_path='token.json'):
        load_dotenv() # Load environment variables
        self.credentials_path = credentials_path
        self.token_path = token_path
        logger.info("Initializing GoogleCalendarService.")
        self.service = self._authenticate()
        
        # Load timezone from .env
        timezone_str = os.getenv("CALENDAR_TIMEZONE")
        if not timezone_str:
            logger.error("CALENDAR_TIMEZONE not found in .env file. Please set your timezone (e.g., 'America/New_York', 'Asia/Kolkata').")
            raise ValueError("CALENDAR_TIMEZONE not found in .env file")
        try:
            self.timezone = pytz.timezone(timezone_str)
        except pytz.UnknownTimeZoneError:
            logger.error(f"Unknown timezone '{timezone_str}' specified in CALENDAR_TIMEZONE. Please use a valid tz database name.")
            raise ValueError(f"Unknown timezone '{timezone_str}'")

        logger.info(f"GoogleCalendarService initialized. Configured timezone: {self.timezone}")

    def _authenticate(self):
        """Shows user how to authenticate with Google Calendar API."""
        creds = None
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            logger.info(f"Loaded credentials from {self.token_path}")
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing expired Google credentials.")
                creds.refresh(Request())
            else:
                logger.info("No valid Google credentials found. Initiating new authentication flow.")
                if not os.path.exists(self.credentials_path):
                    logger.error(f"Google client_secret.json not found at {self.credentials_path}.")
                    raise FileNotFoundError(
                        f"Google client_secret.json not found at {self.credentials_path}. "
                        "Please download it from Google Cloud Console and place it in the project root."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
                logger.info("Authentication successful. Saving credentials.")
            with open(self.token_path, "w") as token:
                token.write(creds.to_json())
                logger.info(f"Credentials saved to {self.token_path}")
        try:
            service = build("calendar", "v3", credentials=creds)
            logger.info("Google Calendar API service built successfully.")
            return service
        except HttpError as error:
            logger.error(f"An error occurred during Google Calendar API service build: {error}", exc_info=True)
            return None

    def create_event(self, summary: str, start_datetime: datetime.datetime, end_datetime: datetime.datetime = None, description: str = None):
        """
        Creates a new event on the user's primary Google Calendar.
        :param summary: Title of the event.
        :param start_datetime: datetime object for the start of the event.
        :param end_datetime: Optional datetime object for the end of the event. If None, defaults to 1 hour after start.
        :param description: Optional description for the event.
        :return: The created event object or None if an error occurred.
        """
        logger.info(f"Attempting to create event: '{summary}' starting at {start_datetime}")
        if end_datetime is None:
            end_datetime = start_datetime + datetime.timedelta(hours=1)

        # Ensure datetimes are timezone-aware
        if start_datetime.tzinfo is None:
            start_datetime = self.timezone.localize(start_datetime)
        if end_datetime.tzinfo is None:
            end_datetime = self.timezone.localize(end_datetime)

        event = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start_datetime.isoformat(),
                'timeZone': str(self.timezone),
            },
            'end': {
                'dateTime': end_datetime.isoformat(),
                'timeZone': str(self.timezone),
            },
        }
        logger.debug(f"Event body prepared: {event}")

        try:
            event = self.service.events().insert(calendarId='primary', body=event).execute()
            logger.info(f"Event created successfully: {event.get('htmlLink')}")
            return event
        except HttpError as error:
            logger.error(f"An error occurred while creating event: {error}", exc_info=True)
            return None

if __name__ == '__main__':
    # This part is for testing the calendar service directly.
    # You would need client_secret.json in the root directory for this to work.
    # Example usage:
    # from utils.logger import setup_logging
    # setup_logging()
    # calendar_service = GoogleCalendarService()
    #
    # # Create a test event for tomorrow at 10 AM
    # tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    # start_time = datetime.datetime.combine(tomorrow, datetime.time(10, 0, 0))
    #
    # calendar_service.create_event(
    #     summary="Test Event from Bot",
    #     start_datetime=start_time,
    #     description="This is a test event created by your Personal Assistant bot."
    # )
    logger.info("GoogleCalendarService class defined. Run main.py to integrate.")
