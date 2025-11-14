import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
import logging
from datetime import date # Import date for current date

logger = logging.getLogger(__name__)

class EventParser:
    def __init__(self):
        load_dotenv()
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not self.gemini_api_key:
            logger.error("GEMINI_API_KEY not found in .env file")
            raise ValueError("GEMINI_API_KEY not found in .env file")
        
        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-flash-latest') # Using gemini-flash-latest for text generation
        logger.info("EventParser initialized with Gemini model: gemini-flash-latest.")

    def parse_event_from_text(self, text: str) -> dict | None:
        """
        Parses a natural language text to extract event details (title, date, time).
        Returns a dictionary with 'title', 'date' (YYYY-MM-DD), 'time' (HH:MM:SS),
        or None if no event details are found.
        """
        logger.info(f"Attempting to parse event from text: '{text}'")
        
        current_date = date.today().isoformat() # Get today's date in YYYY-MM-DD format

        prompt = f"""
        Today's date is {current_date}.
        Extract event details (title, date, start time, and end time) from the following text.
        If a date is mentioned relative to today (e.g., "tomorrow", "next Monday"), resolve it to an absolute date (YYYY-MM-DD) based on today's date.
        If a start time is mentioned, resolve it to HH:MM:SS format.
        If an end time is mentioned, resolve it to HH:MM:SS format.
        If only a date is provided, assume the start time is 09:00:00 and end time is 10:00:00.
        If only a start time is provided, assume the date is today and end time is 1 hour after start time.
        If no date or time is provided, return null for date, start_time, and end_time.
        Return the output as a JSON object with keys 'title', 'date', 'start_time', and 'end_time'.
        If no event details can be extracted, return an empty JSON object {{}}.

        Example 1: "Remind me to go to the dentist on Tuesday from 2 PM to 3 PM" (assuming today is 2025-11-14)
        Output 1: {{"title": "Go to the dentist", "date": "2025-11-18", "start_time": "14:00:00", "end_time": "15:00:00"}}

        Example 2: "Team meeting tomorrow at 4pm for an hour" (assuming today is 2025-11-14)
        Output 2: {{"title": "Team meeting", "date": "2025-11-15", "start_time": "16:00:00", "end_time": "17:00:00"}}

        Example 3: "Buy groceries"
        Output 3: {{"title": "Buy groceries", "date": null, "start_time": null, "end_time": null}}

        Example 4: "Lunch with John next Monday at 1 PM" (assuming today is 2025-11-14)
        Output 4: {{"title": "Lunch with John", "date": "2025-11-24", "start_time": "13:00:00", "end_time": "14:00:00"}}

        Text: "{text}"
        """
        try:
            response = self.model.generate_content(prompt)
            json_output = response.text.strip()
            logger.debug(f"Gemini API raw response: {json_output}")

            # Strip markdown code block fences if present
            if json_output.startswith("```json") and json_output.endswith("```"):
                json_output = json_output[len("```json"): -len("```")].strip()
            elif json_output.startswith("```") and json_output.endswith("```"):
                json_output = json_output[len("```"): -len("```")].strip()

            event_data = json.loads(json_output)
            
            # Basic validation
            if "title" in event_data and (event_data.get("date") or event_data.get("start_time")):
                logger.info(f"Successfully parsed event: {event_data}")
                return event_data
            elif "title" in event_data and event_data.get("date") is None and event_data.get("start_time") is None:
                logger.info(f"Parsed event with only title: {event_data}")
                return event_data
            logger.info("No valid event details extracted from Gemini response.")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding error from Gemini response: {e}. Raw response: '{json_output}'")
            return None
        except Exception as e:
            logger.error(f"Error parsing event with Gemini: {e}", exc_info=True)
            return None

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
