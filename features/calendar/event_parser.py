import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)

class EventParser:
    def __init__(self, calendar_service):
        load_dotenv()
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not self.gemini_api_key:
            logger.error("GEMINI_API_KEY not found in .env file")
            raise ValueError("GEMINI_API_KEY not found in .env file")
        
        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-flash-latest')
        self.calendar_service = calendar_service
        logger.info("EventParser initialized with Gemini model: gemini-flash-latest.")

    def parse_event_from_text(self, text: str) -> list[dict]:
        """
        Parses a natural language text to extract event details.
        Returns a list of dictionaries, where each dictionary contains event details.
        """
        logger.info(f"Attempting to parse event(s) from text: '{text}'")
        
        current_date = date.today().isoformat()

        calendar_info = ""
        if self.calendar_service and self.calendar_service.calendars:
            calendar_info = "Based on the user's available calendars, suggest the most appropriate calendar for the event. Available calendars:\n"
            for cal in self.calendar_service.calendars:
                summary = cal.get('summary', 'Unnamed Calendar')
                calendar_id = cal.get('id')
                if calendar_id:
                    calendar_info += f"- Name: {summary}, ID: {calendar_id}\n"
            calendar_info += "\n"

        prompt = f"""
        Today's date is {current_date}.
        {calendar_info}
        Extract all event details (title, date, start time, end time) from the following text.
        If a date is mentioned relative to today (e.g., "tomorrow", "next Monday"), resolve it to an absolute date (YYYY-MM-DD).
        Resolve times to HH:MM:SS format.
        If no suitable calendar is found, suggest 'primary' as the calendar ID.
        Return the output as a JSON array of objects. Each object must have keys 'title', 'date', 'start_time', 'end_time', and 'calendar_id'.
        If no events can be extracted, return an empty JSON array [].

        Example Text: \"Team meeting tomorrow at 4pm for an hour and then dinner with Jane at 7pm\"
        Example Output: [
            {{\"title\": \"Team meeting\", \"date\": \"{(date.today() + timedelta(days=1)).isoformat()}\", \"start_time\": \"16:00:00\", \"end_time\": \"17:00:00\", \"calendar_id\": \"primary\"}},
            {{\"title\": \"Dinner with Jane\", \"date\": \"{(date.today() + timedelta(days=1)).isoformat()}\", \"start_time\": \"19:00:00\", \"end_time\": \"20:00:00\", \"calendar_id\": \"primary\"}}
        ]

        Text to parse: \"{text}\" 
        """
        try:
            response = self.model.generate_content(prompt)
            json_output = response.text.strip()
            logger.debug(f"Gemini API raw response: {json_output}")

            if json_output.startswith("```json") and json_output.endswith("```"):
                json_output = json_output[len("```json"):-len("```")].strip()
            elif json_output.startswith("```") and json_output.endswith("```"):
                json_output = json_output[len("```"):-len("```")].strip()

            event_list = json.loads(json_output)
            
            if not isinstance(event_list, list):
                logger.error(f"Gemini response was not a list: {json_output}")
                return []

            for event in event_list:
                if event.get('title') == 'Swarit':
                    event['title'] += ' YAY'

            logger.info(f"Successfully parsed {len(event_list)} event(s) from AI.")
            return event_list
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding error from Gemini response: {e}. Raw response: '{json_output}'")
            return []
        except Exception as e:
            logger.error(f"Error parsing event with Gemini: {e}", exc_info=True)
            return []

if __name__ == '__main__':
    # This part is for direct testing of event_parser.py,
    # but main.py will be the primary entry point.
    # Ensure logging is set up if running this directly for testing.
    # from utils.logger import setup_logging
    # setup_logging()
    parser = EventParser()
    
    # Test cases
    print("Testing 'Remind me to go to the dentist on Tuesday at 2 PM'")
    event = parser.parse_event_from_text("Remind me to go to the dentist on Tuesday at 2 PM")
    print(event)

    print("\nTesting 'Team meeting tomorrow at 4pm'")
    event = parser.parse_event_from_text("Team meeting tomorrow at 4pm")
    print(event)

    print("\nTesting 'Buy groceries'")
    event = parser.parse_event_from_text("Buy groceries")
    print(event)

    print("\nTesting 'Lunch with John next Monday'")
    event = parser.parse_event_from_text("Lunch with John next Monday")
    print(event)