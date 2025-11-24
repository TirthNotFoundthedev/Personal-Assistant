import os
import datetime
import pytz
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]

class GoogleCalendarService:
    def __init__(self, credentials_path='client_secret.json', token_path='token.json'):
        load_dotenv()
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = self._authenticate()
        timezone_str = os.getenv("CALENDAR_TIMEZONE", "UTC")
        try:
            self.timezone = pytz.timezone(timezone_str)
        except pytz.UnknownTimeZoneError:
            logger.error(f"Unknown timezone '{timezone_str}'. Defaulting to UTC.")
            self.timezone = pytz.timezone("UTC")

    def _authenticate(self):
        creds = None
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Error refreshing token: {e}. Deleting token and re-authenticating.")
                    os.remove(self.token_path)
                    creds = None # Force re-authentication
            if not creds:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(f"'{self.credentials_path}' not found.")
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(self.token_path, "w") as token:
                token.write(creds.to_json())
        return build("calendar", "v3", credentials=creds)

    def create_event(self, summary: str, start_datetime: datetime.datetime, end_datetime: datetime.datetime, calendar_id: str = 'primary'):
        if start_datetime.tzinfo is None:
            start_datetime = self.timezone.localize(start_datetime)
        if end_datetime.tzinfo is None:
            end_datetime = self.timezone.localize(end_datetime)

        event = {
            'summary': summary,
            'start': {'dateTime': start_datetime.isoformat()},
            'end': {'dateTime': end_datetime.isoformat()},
        }
        try:
            created_event = self.service.events().insert(calendarId=calendar_id, body=event).execute()
            logger.info(f"Event created: {created_event.get('htmlLink')}")
            return created_event
        except HttpError as error:
            logger.error(f"An error occurred: {error}")
            return None

    def get_upcoming_events(self, num_events: int = 20):
        now = datetime.datetime.now(self.timezone)
        try:
            events_result = self.service.events().list(
                calendarId='primary', timeMin=now.isoformat(),
                maxResults=num_events, singleEvents=True,
                orderBy='startTime'
            ).execute()
            return events_result.get('items', [])
        except HttpError as error:
            logger.error(f"An error occurred: {error}")
            return []

    def get_writable_calendars(self) -> list:
        """Fetches all calendars the user has write access to."""
        writable_calendars = []
        try:
            calendar_list = self.service.calendarList().list().execute()
            for calendar_list_entry in calendar_list.get('items', []):
                if calendar_list_entry.get('accessRole') in ['writer', 'owner']:
                    writable_calendars.append(calendar_list_entry)
            return writable_calendars
        except HttpError as error:
            logger.error(f"An error occurred while fetching calendars: {error}")
            return []

    def get_all_calendars(self) -> list:
        """Fetches all calendars the user has access to."""
        try:
            calendar_list = self.service.calendarList().list().execute()
            return calendar_list.get('items', [])
        except HttpError as error:
            logger.error(f"An error occurred while fetching all calendars: {error}")
            return []

    def get_events_in_range(self, calendar_id: str, start_datetime: datetime.datetime, end_datetime: datetime.datetime) -> list:
        """
        Fetches events for a specific calendar within a given time range.
        :param calendar_id: The ID of the calendar to fetch events from.
        :param start_datetime: The start of the time range (datetime object).
        :param end_datetime: The end of the time range (datetime object).
        :return: A list of event dictionaries.
        """
        try:
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=start_datetime.isoformat(),
                timeMax=end_datetime.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            return events_result.get('items', [])
        except HttpError as error:
            logger.error(f"An error occurred while fetching events for calendar {calendar_id}: {error}")
            return []
