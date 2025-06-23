import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv
from langchain_core.tools import tool
from datetime import datetime, timezone, timedelta

load_dotenv(override=True)

SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')
credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('calendar', 'v3', credentials=credentials)
CALENDAR_ID = 'a1778e08499a4681976275ad5aacde3ae99efec8fe3f93e65212406be51e689c@group.calendar.google.com'

@tool
def get_calendar_event(group_id: str):
    """
    Retrieves calendar events from a specified Google Calendar that match the given group ID.
    Args:
        group_id (str): The group ID
    """
    result = service.events().list(calendarId=CALENDAR_ID).execute()
    items = result['items']
    if items:
        events_list = []
        for e in items:
            if e["extendedProperties"]["private"]["group_id"] == group_id:
                try:
                    event = {
                                'id': e['id'], 
                                'summary': e['summary'],
                                'description': e['description'],
                                'start': e['start'],
                                'end': e['end']
                            }
                except:
                    event = {
                                'id': e['id'], 
                                'summary': e['summary'],
                                'start': e['start'],
                                'end': e['end']
                            }
                events_list.append(event)
        return events_list
    return 'no events'

@tool
def create_calendar_event(summary: str, start, end, group_id: str, description: str = None):
    """
    Creates a new event in the Google Calendar with the specified details.

    The event will use the 'Asia/Bangkok' time zone.

    Args:
        summary (str): The title or summary of the event.
        start (str): The start datetime of the event in ISO 8601 format (e.g., '2025-06-16T09:00:00').
        end (str): The end datetime of the event in ISO 8601 format (e.g., '2025-06-16T10:00:00').
        group_id (str): The group ID to associate the event with.
        description (str, optional): Additional details or notes for the event.
    """
    event = {
        'summary': summary,
        'description': description,
        'start': {
            'dateTime': start,
            'timeZone': 'Asia/Bangkok'
        },
        'end': {
            'dateTime': end,
            'timeZone': 'Asia/Bangkok'
        },
        "extendedProperties": {
            "private": {
                "group_id": group_id
            }
        }
    }
    result = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
    return f'Event created: {result['id']}'

@tool
def delete_calendar_event(event_id: str):
    """
    Deletes a specific event from the Google Calendar using its event ID.

    Args:
        event_id (str): The unique identifier of the event to be deleted.
    """
    try:
        service.events().delete(calendarId=CALENDAR_ID, eventId=event_id).execute()
        return f'Successfully Delete event: {event_id}'
    except Exception as e:
        return f'Failed to Delete Event: {e}'

def get_calendar_next_hour():
    now = datetime.now(timezone(timedelta(hours = 7))).isoformat()
    next_q = (datetime.now(timezone(timedelta(hours = 7))) + timedelta(minutes=15)).isoformat()
    result = service.events().list(calendarId=CALENDAR_ID,
                                    timeMin=now,  
                                    timeMax=next_q,
                                    singleEvents=True,
                                    orderBy='startTime'
                                    ).execute()
    items = result['items']
    if items:
        events_list = []
        for e in items:
            try:
                event = {
                            'id': e['id'], 
                            'summary': e['summary'],
                            'description': e['description'],
                            'start': e['start'],
                            'end': e['end'],
                            'groupid': e["extendedProperties"]["private"]["group_id"]
                        }
            except:
                event = {
                            'id': e['id'], 
                            'summary': e['summary'],
                            'start': e['start'],
                            'end': e['end'],
                            'groupid': e["extendedProperties"]["private"]["group_id"]
                        }
            if now < event['start']['dateTime']:
                events_list.append(event)
        return events_list
    return None