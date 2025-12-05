import os
import requests
import base64
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

TOGGL_API_KEY = os.getenv("TOGGL_API_KEY")
TOGGL_API_BASE_URL = "https://api.track.toggl.com/api/v9"

def _get_headers():
    """Returns the authorization headers for Toggl API."""
    if not TOGGL_API_KEY:
        raise ValueError("TOGGL_API_KEY not set in environment variables.")
    
    auth_string = f"{TOGGL_API_KEY}:api_token"
    encoded_auth = base64.b64encode(auth_string.encode("ascii")).decode("ascii")
    return {
        "Content-Type": "application/json",
        "Authorization": f"Basic {encoded_auth}"
    }

def get_workspace_id():
    """Fetches the default workspace ID for the user."""
    headers = _get_headers()
    response = requests.get(f"{TOGGL_API_BASE_URL}/me", headers=headers)
    response.raise_for_status()
    data = response.json()
    if data and "default_workspace_id" in data:
        return data["default_workspace_id"]
    return None

def get_clients():
    """Fetches all clients for the default workspace."""
    workspace_id = get_workspace_id()
    if not workspace_id:
        return []

    headers = _get_headers()
    response = requests.get(f"{TOGGL_API_BASE_URL}/workspaces/{workspace_id}/clients", headers=headers)
    response.raise_for_status()
    return response.json()

def get_projects(client_id=None):
    """
    Fetches all projects for the default workspace, optionally filtered by client.
    Note: Toggl API v9 does not directly support filtering projects by client_id at the endpoint level.
    We fetch all and filter client-side.
    """
    workspace_id = get_workspace_id()
    if not workspace_id:
        return []

    headers = _get_headers()
    response = requests.get(f"{TOGGL_API_BASE_URL}/workspaces/{workspace_id}/projects", headers=headers)
    response.raise_for_status()
    
    all_projects = response.json()
    if client_id:
        return [p for p in all_projects if p.get("client_id") == client_id]
    return all_projects

def start_time_entry(description, project_id=None):
    """Starts a new time entry."""
    workspace_id = get_workspace_id()
    if not workspace_id:
        raise ValueError("Could not determine workspace ID.")

    headers = _get_headers()
    payload = {
        "billable": False,
        "description": description,
        "project_id": project_id,
        "workspace_id": workspace_id,
        "created_with": "Personal Assistant Bot"
    }
    response = requests.post(f"{TOGGL_API_BASE_URL}/workspaces/{workspace_id}/time_entries", headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

def stop_active_time_entry():
    """Stops the currently running time entry."""
    headers = _get_headers()
    response = requests.get(f"{TOGGL_API_BASE_URL}/me/time_entries/current", headers=headers)
    response.raise_for_status()
    current_entry = response.json()

    if not current_entry:
        return None # No active time entry

    time_entry_id = current_entry["id"]
    response = requests.put(f"{TOGGL_API_BASE_URL}/time_entries/{time_entry_id}/stop", headers=headers, json={{}})
    response.raise_for_status()
    return response.json()

def create_time_entry(description, duration_seconds, project_id=None, start_time=None):
    """
    Creates a new time entry for a past duration.
    If start_time is not provided, it assumes the entry ended now and started 'duration_seconds' ago.
    'duration_seconds' should be negative for ongoing entries, but for this function, it's a fixed duration.
    """
    workspace_id = get_workspace_id()
    if not workspace_id:
        raise ValueError("Could not determine workspace ID.")

    headers = _get_headers()
    
    # Toggl expects 'start' and 'duration' (in seconds, negative for running entry)
    # and 'stop' in ISO 8601 format.
    # For 'create_time_entry', we assume it's a finished entry.
    from datetime import datetime, timezone, timedelta
    
    now = datetime.now(timezone.utc)
    if start_time:
        # Assuming start_time is a datetime object in UTC or timezone-aware
        start = start_time.isoformat()
        stop = (start_time + timedelta(seconds=duration_seconds)).isoformat()
    else:
        stop = now.isoformat()
        start = (now - timedelta(seconds=duration_seconds)).isoformat()

    payload = {
        "billable": False,
        "description": description,
        "project_id": project_id,
        "workspace_id": workspace_id,
        "created_with": "Personal Assistant Bot",
        "start": start,
        "stop": stop,
        "duration": duration_seconds # Positive for finished entry
    }
    
    response = requests.post(f"{TOGGL_API_BASE_URL}/workspaces/{workspace_id}/time_entries", headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

# Example usage (for testing purposes, can be removed later)
if __name__ == '__main__':
    try:
        print("Fetching workspace ID...")
        ws_id = get_workspace_id()
        print(f"Workspace ID: {ws_id}")

        print("\nFetching clients...")
        clients = get_clients()
        for client in clients:
            print(f"Client ID: {client['id']}, Name: {client['name']}")

        if clients:
            first_client_id = clients[0]['id']
            print(f"\nFetching projects for client ID {first_client_id}...")
            projects = get_projects(first_client_id)
            for project in projects:
                print(f"Project ID: {project['id']}, Name: {project['name']}")
        
        # Example of starting a time entry (commented out to prevent accidental API calls)
        # print("\nStarting a time entry...")
        # new_entry = start_time_entry("Test task from bot", project_id=1234567) # Replace with a real project_id
        # print(f"Started entry: {new_entry['data']['description']} at {new_entry['data']['start']}")

        # Example of stopping a time entry (commented out)
        # print("\nStopping active time entry...")
        # stopped_entry = stop_active_time_entry()
        # if stopped_entry:
        #     print(f"Stopped entry: {stopped_entry['data']['description']}")
        # else:
        #     print("No active time entry to stop.")

        # Example of creating a past time entry (commented out)
        # print("\nCreating a past time entry...")
        # from datetime import datetime, timedelta, timezone
        # past_start = datetime.now(timezone.utc) - timedelta(hours=1)
        # past_entry = create_time_entry("Past task from bot", 3600, project_id=1234567, start_time=past_start)
        # print(f"Created past entry: {past_entry['data']['description']}")

    except Exception as e:
        print(f"An error occurred: {e}")
