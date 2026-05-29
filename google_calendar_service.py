from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from quickstart import get_calendar_service
from datetime import datetime, timedelta

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


# delete fucntion 
def delete_event_by_id(event_id):
    service = get_calendar_service()

    service.events().delete(
        calendarId="primary",
        eventId=event_id
    ).execute()

    return True

# getting available slots for rescheduling getting suggestions for next available slots after the originally scheduled time

def get_available_slots(info, number_of_slots=3):
    # Suggest candidate slots within 7 days from the requested date.
    # If the user asks for more options, skip previously shown slots.
    # The selected slot is checked again before creating the event.

    start_datetime, end_datetime = build_start_end_datetime(info)

    duration_minutes = info["duration_minutes"]
    slot_suggestion_offset = info.get("slot_suggestion_offset", 0)

    all_candidate_slots = []

    for day_offset in range(7):
        current_day = start_datetime + timedelta(days=day_offset)

        # Simple candidate times for each day.
        candidate_times = [
            current_day.replace(hour=9, minute=0, second=0, microsecond=0),
            current_day.replace(hour=13, minute=0, second=0, microsecond=0),
            current_day.replace(hour=15, minute=0, second=0, microsecond=0),
        ]

        for candidate_start in candidate_times:
            candidate_end = candidate_start + timedelta(minutes=duration_minutes)

            # Do not suggest the original requested time again.
            if candidate_start == start_datetime:
                continue

            all_candidate_slots.append((candidate_start, candidate_end))

    return all_candidate_slots[
        slot_suggestion_offset:slot_suggestion_offset + number_of_slots
    ]