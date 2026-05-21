from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from quickstart import get_calendar_service


def build_start_end_datetime(info):
    date = info["date"]
    time = info["time"]
    duration_minutes = info["duration_minutes"]
    timezone = info["timezone"]

    timezone_object = ZoneInfo(timezone)

    start_datetime = datetime.fromisoformat(date + "T" + time)
    start_datetime = start_datetime.replace(tzinfo=timezone_object)

    end_datetime = start_datetime + timedelta(minutes=duration_minutes)

    return start_datetime, end_datetime


def check_calendar_conflict(info):
    service = get_calendar_service()

    timezone = info["timezone"]
    start_datetime, end_datetime = build_start_end_datetime(info)

    events_result = service.events().list(
        calendarId="primary",
        timeMin=start_datetime.isoformat(),
        timeMax=end_datetime.isoformat(),
        timeZone=timezone,
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    events = events_result.get("items", [])

    if len(events) > 0:
        return True, events

    return False, []


def create_event_from_info(info):
    service = get_calendar_service()

    timezone = info["timezone"]
    start_datetime, end_datetime = build_start_end_datetime(info)

    event = {
        "summary": info["event_title"],
        "description": "Created by Calendar Scheduling Agent.",
        "start": {
            "dateTime": start_datetime.isoformat(),
            "timeZone": timezone,
        },
        "end": {
            "dateTime": end_datetime.isoformat(),
            "timeZone": timezone,
        },
    }

    created_event = service.events().insert(
        calendarId="primary",
        body=event
    ).execute()

    return created_event


def print_conflicts(events):
    print("\nConflict detected. You already have event(s) at this time:")

    for event in events:
        title = event.get("summary", "No Title")
        start = event["start"].get("dateTime", event["start"].get("date"))
        end = event["end"].get("dateTime", event["end"].get("date"))

        print(f"- {title}: {start} to {end}")