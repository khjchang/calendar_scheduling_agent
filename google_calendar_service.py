from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from quickstart import get_calendar_service
import re


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

# Delete an existing calendar event 

def delete_event_by_id(event_id):
   
    service = get_calendar_service()

    service.events().delete(
        calendarId="primary",
        eventId=event_id
    ).execute()

    return True

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

    participants = info.get("participants", [])
    valid_participants = []

    for participant in participants:
        if is_valid_email(participant):
            valid_participants.append(participant)

    if valid_participants:
        event["attendees"] = []

        for participant in valid_participants:
            event["attendees"].append({
                "email": participant
            })

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


def slot_has_conflict(start_datetime, end_datetime, timezone):
    service = get_calendar_service()

    events_result = service.events().list(
        calendarId="primary",
        timeMin=start_datetime.isoformat(),
        timeMax=end_datetime.isoformat(),
        timeZone=timezone,
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    events = events_result.get("items", [])

    return len(events) > 0


def get_available_slots(info, number_of_slots=3):
    # Suggest available candidate slots within 7 days from the requested date.
    # Each candidate slot is checked against the real Google Calendar before being suggested.

    start_datetime, _ = build_start_end_datetime(info)

    timezone = info["timezone"]
    duration_minutes = info["duration_minutes"]
    slot_suggestion_offset = info.get("slot_suggestion_offset", 0)

    candidate_hours = [9, 10, 11, 13, 14, 15, 16, 17]

    available_slots = []
    valid_slot_count = 0

    for day_offset in range(7):
        current_day = start_datetime + timedelta(days=day_offset)

        for hour in candidate_hours:
            candidate_start = current_day.replace(
                hour=hour,
                minute=0,
                second=0,
                microsecond=0
            )

            candidate_end = candidate_start + timedelta(minutes=duration_minutes)

            # Do not suggest the original requested time again.
            if candidate_start == start_datetime:
                continue

            # Do not suggest occupied slots.
            if slot_has_conflict(candidate_start, candidate_end, timezone):
                continue

            # Skip previously shown available slots when user asks for more options.
            if valid_slot_count < slot_suggestion_offset:
                valid_slot_count += 1
                continue

            available_slots.append((candidate_start, candidate_end))
            valid_slot_count += 1

            if len(available_slots) >= number_of_slots:
                return available_slots

    return available_slots

def find_matching_events(info):
    # Find calendar events on a date.
    # If event_title exists, return only matching events.
    # If event_title is missing, return all events on that date.

    service = get_calendar_service()

    event_title = info.get("event_title")
    date = info.get("date")
    timezone = info.get("timezone")

    if not date or not timezone:
        return []

    timezone_object = ZoneInfo(timezone)

    day_start = datetime.fromisoformat(date + "T00:00")
    day_start = day_start.replace(tzinfo=timezone_object)

    day_end = datetime.fromisoformat(date + "T23:59")
    day_end = day_end.replace(tzinfo=timezone_object)

    events_result = service.events().list(
        calendarId="primary",
        timeMin=day_start.isoformat(),
        timeMax=day_end.isoformat(),
        timeZone=timezone,
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    events = events_result.get("items", [])

    # If the user did not give a specific title,
    # return all events on that date.
    if not event_title:
        return events

    matching_events = []

    for event in events:
        title = event.get("summary", "").lower()

        if event_title.lower() in title:
            matching_events.append(event)

    return matching_events


def update_event_by_id(event_id, info):
    # Update an existing calendar event by Google Calendar event ID.
    service = get_calendar_service()

    timezone = info["timezone"]
    start_datetime, end_datetime = build_start_end_datetime(info)

    event_body = {
        "summary": info["event_title"],
        "description": "Rescheduled by Calendar Scheduling Agent.",
        "start": {
            "dateTime": start_datetime.isoformat(),
            "timeZone": timezone,
        },
        "end": {
            "dateTime": end_datetime.isoformat(),
            "timeZone": timezone,
        },
    }

    participants = info.get("participants", [])

    if participants:
        event_body["attendees"] = []

        for participant in participants:
            event_body["attendees"].append({
                "email": participant
            })

    updated_event = service.events().update(
        calendarId="primary",
        eventId=event_id,
        body=event_body
    ).execute()

    return updated_event


def is_valid_email(text):
    # Check if text looks like an email address.
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", text) is not None