from typing import List, Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Optional
from pydantic import BaseModel
from typing import List, Optional
from pydantic import BaseModel
import re
import json

from google_calendar_service import (
    check_calendar_conflict,
    create_event_from_info,
    get_available_slots,
    delete_event_by_id,
    update_event_by_id,
    find_matching_events,
    is_valid_email
)

from extract_prompt import (
    extract_scheduling_info,
    update_scheduling_info,
    interpret_conflict_response,
    interpret_event_choice,
    format_event_time
)

from validation import check_scheduling_info
from manage_date import fix_year_if_missing


app = FastAPI(title="Calendar Scheduling Agent Tool API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CalendarEventInfo(BaseModel):
    action_type: Optional[str] = None
    event_title: Optional[str] = None
    date: str
    time: str
    timezone: str
    duration_minutes: int = 30
    participants: List[str] = []


class DateSearchInfo(BaseModel):
    action_type: Optional[str] = None
    event_title: Optional[str] = None
    date: str
    timezone: str
    duration_minutes: int = 30
    participants: List[str] = []


class DeleteRequest(BaseModel):
    event_id: str


class RescheduleRequest(BaseModel):
    event_id: str
    event_title: str
    date: str
    time: str
    timezone: str
    duration_minutes: int = 30
    participants: List[str] = []


class AgentChatRequest(BaseModel):
    session_id: str
    message: str


chat_sessions = {}


def model_to_dict(model):
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


@app.get("/")
def root():
    return {
        "message": "Calendar Scheduling Agent Tool API is running.",
        "endpoints": [
            "/check_conflict",
            "/get_available_slots",
            "/create_event",
            "/find_matching_events",
            "/delete_event",
            "/reschedule_event",
            "/agent_chat"
        ]
    }


@app.post("/check_conflict")
def check_conflict(info: CalendarEventInfo):
    try:
        data = model_to_dict(info)
        has_conflict, conflicts = check_calendar_conflict(data)

        return {
            "has_conflict": has_conflict,
            "conflicts": conflicts
        }

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@app.post("/get_available_slots")
def api_get_available_slots(info: CalendarEventInfo):
    try:
        data = model_to_dict(info)
        slots = get_available_slots(data)

        formatted_slots = []

        for start_time, end_time in slots:
            formatted_slots.append({
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            })

        return {
            "available_slots": formatted_slots
        }

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@app.post("/create_event")
def api_create_event(info: CalendarEventInfo):
    try:
        data = model_to_dict(info)

        has_conflict, conflicts = check_calendar_conflict(data)

        if has_conflict:
            return {
                "created": False,
                "reason": "conflict_detected",
                "conflicts": conflicts
            }

        created_event = create_event_from_info(data)

        return {
            "created": True,
            "event_id": created_event.get("id"),
            "html_link": created_event.get("htmlLink"),
            "summary": created_event.get("summary")
        }

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@app.post("/find_matching_events")
def api_find_matching_events(info: DateSearchInfo):
    try:
        data = model_to_dict(info)
        events = find_matching_events(data)

        simplified_events = []

        for event in events:
            simplified_events.append({
                "id": event.get("id"),
                "summary": event.get("summary", "No Title"),
                "start": event.get("start"),
                "end": event.get("end"),
                "html_link": event.get("htmlLink")
            })

        return {
            "events": simplified_events
        }

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@app.post("/delete_event")
def api_delete_event(request: DeleteRequest):
    try:
        delete_event_by_id(request.event_id)

        return {
            "deleted": True,
            "event_id": request.event_id
        }

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@app.post("/reschedule_event")
def api_reschedule_event(request: RescheduleRequest):
    try:
        data = model_to_dict(request)
        event_id = data.pop("event_id")

        has_conflict, conflicts = check_calendar_conflict(data)

        if has_conflict:
            return {
                "rescheduled": False,
                "reason": "conflict_detected",
                "conflicts": conflicts
            }

        updated_event = update_event_by_id(event_id, data)

        return {
            "rescheduled": True,
            "event_id": updated_event.get("id"),
            "html_link": updated_event.get("htmlLink"),
            "summary": updated_event.get("summary")
        }

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


def clean_participants(info):
    participants = info.get("participants", [])
    valid_participants = []

    for participant in participants:
        if is_valid_email(participant):
            valid_participants.append(participant)

    info["participants"] = valid_participants
    return info


def format_events_for_chat(events, timezone):
    lines = []

    for index, event in enumerate(events):
        title = event.get("summary", "No Title")

        start_raw = event["start"].get("dateTime", event["start"].get("date"))
        end_raw = event["end"].get("dateTime", event["end"].get("date"))

        start = format_event_time(start_raw, timezone)
        end = format_event_time(end_raw, timezone)

        lines.append(f"{index + 1}. {title}\n   Time: {start} - {end}")

    return "\n".join(lines)


def format_datetime_with_date(raw_datetime, timezone):
    dt = datetime.fromisoformat(raw_datetime.replace("Z", "+00:00"))
    dt = dt.astimezone(ZoneInfo(timezone))
    return dt.strftime("%Y-%m-%d %I:%M %p %Z")


def format_time_only(raw_datetime, timezone):
    dt = datetime.fromisoformat(raw_datetime.replace("Z", "+00:00"))
    dt = dt.astimezone(ZoneInfo(timezone))
    return dt.strftime("%I:%M %p %Z")


def format_conflicts_for_chat(conflicts, timezone):
    lines = []

    for event in conflicts:
        title = event.get("summary", "No Title")

        start_raw = event["start"].get("dateTime", event["start"].get("date"))
        end_raw = event["end"].get("dateTime", event["end"].get("date"))

        start = format_datetime_with_date(start_raw, timezone)
        end = format_time_only(end_raw, timezone)

        lines.append(f"- {title}: {start} - {end}")

    return "\n".join(lines)


def format_slots_for_chat(slots):
    lines = []

    for index, slot in enumerate(slots):
        start_time = slot[0]
        end_time = slot[1]

        start = start_time.strftime("%Y-%m-%d %I:%M %p %Z")
        end = end_time.strftime("%I:%M %p %Z")

        lines.append(
            f"{index + 1}. {start} - {end}"
        )

    return "\n".join(lines)


def format_created_event_time(created_event, timezone):
    start_raw = created_event["start"].get(
        "dateTime",
        created_event["start"].get("date")
    )

    return format_event_time(start_raw, timezone)


def handle_valid_agent_info(session_id, info):
    action = info.get("action_type")

    if action == "create":
        has_conflict, conflicts = check_calendar_conflict(info)

        if has_conflict:
            available_slots = get_available_slots(info)

            chat_sessions[session_id] = {
                "state": "create_conflict",
                "info": info
            }

            reply = (
                "I found a conflict at that time:\n\n"
                f"{format_conflicts_for_chat(conflicts, info.get('timezone'))}\n\n"
                "Here are some available slots:\n\n"
                f"{format_slots_for_chat(available_slots)}\n\n"
                "You can choose a number, give another time, ask for more options, or say cancel."
            )

            return {"reply": reply}

        created_event = create_event_from_info(info)
        display_time = format_created_event_time(created_event, info.get("timezone"))

        reply = (
            "Event created successfully.\n\n"
            f"Title: {info.get('event_title')}\n"
            f"Date: {info.get('date')}\n"
            f"Time: {display_time}\n"
            f"Timezone: {info.get('timezone')}\n"
            f"Duration: {info.get('duration_minutes')} minutes\n"
        )

        participants = info.get("participants", [])

        if participants:
            reply += f"Participants: {', '.join(participants)}\n"

        # reply += f"Calendar link: {created_event.get('htmlLink')}"

        chat_sessions.pop(session_id, None)
        return {"reply": reply}

    if action == "delete":
        matching_events = find_matching_events(info)

        if len(matching_events) == 0:
            chat_sessions.pop(session_id, None)
            return {"reply": "I could not find any events on that date."}

        chat_sessions[session_id] = {
            "state": "delete_choose",
            "info": info,
            "events": matching_events
        }

        reply = (
            f"I found these event(s) on {info.get('date')} ({info.get('timezone')}):\n\n"
            f"{format_events_for_chat(matching_events, info.get('timezone'))}\n\n"
            "Which event should I delete? You can enter a number, answer naturally, or type cancel."
        )

        return {"reply": reply}

    if action == "reschedule":
        matching_events = find_matching_events(info)

        if len(matching_events) == 0:
            chat_sessions.pop(session_id, None)
            return {"reply": "I could not find any events on that date."}

        chat_sessions[session_id] = {
            "state": "reschedule_choose",
            "info": info,
            "events": matching_events
        }

        reply = (
            f"I found these event(s) on {info.get('date')} ({info.get('timezone')}):\n\n"
            f"{format_events_for_chat(matching_events, info.get('timezone'))}\n\n"
            "Which event should I reschedule? You can enter a number, answer naturally, or type cancel."
        )

        return {"reply": reply}

    return {"reply": "I could not understand that request."}


@app.post("/agent_chat")
def agent_chat(request: AgentChatRequest):
    session_id = request.session_id
    message = request.message.strip()

    session = chat_sessions.get(session_id)


    if session and looks_like_new_top_level_request(message):
        chat_sessions.pop(session_id, None)
        session = None

    try:
        if session:
            state = session.get("state")
            if state == "awaiting_ampm":
                info = session["info"]
                ambiguous_hour = session["ambiguous_hour"]
                ambiguous_minute = session["ambiguous_minute"]

                ampm = interpret_ampm_answer(message)

                if ampm is None:
                    return {
                        "reply": "Please clarify whether you mean AM or PM."
                    }

                info = apply_ampm_to_info(
                    info,
                    ambiguous_hour,
                    ambiguous_minute,
                    ampm
                )

                check_result = check_scheduling_info(info)

                if check_result[0] == False:
                    chat_sessions[session_id] = {
                        "state": "awaiting_clarification",
                        "info": info,
                        "question": check_result[1]
                    }
                    return {"reply": check_result[1]}

                return handle_valid_agent_info(session_id, info)

            if state == "awaiting_clarification":
                info = session["info"]
                question = session["question"]

                if "timezone" in question.lower():
                    info["timezone"] = message
                else:
                    info = update_scheduling_info(info, message, question)

                info = clean_participants(info)
                info = fix_year_if_missing(message, info)

                check_result = check_scheduling_info(info)

                if check_result[0] == False:
                    chat_sessions[session_id] = {
                        "state": "awaiting_clarification",
                        "info": info,
                        "question": check_result[1]
                    }
                    return {"reply": check_result[1]}

                return handle_valid_agent_info(session_id, info)

            if state == "create_conflict":
                info = session["info"]
                conflict_response = interpret_conflict_response(message)

                intent = conflict_response.get("intent")
                choice_number = conflict_response.get("choice")

                if intent == "cancel":
                    chat_sessions.pop(session_id, None)
                    return {"reply": "Cancelled. I will not create the new event."}

                if intent == "choose_slot":
                    available_slots = get_available_slots(info)

                    try:
                        choice_number = int(choice_number)
                    except Exception:
                        return {"reply": "Invalid slot number. Please choose one of the suggested slots."}

                    if choice_number < 1 or choice_number > len(available_slots):
                        return {"reply": f"Invalid slot number. Please choose between 1 and {len(available_slots)}."}

                    selected_slot = available_slots[choice_number - 1]
                    selected_start = selected_slot[0]

                    info["date"] = selected_start.strftime("%Y-%m-%d")
                    info["time"] = selected_start.strftime("%H:%M")

                    return handle_valid_agent_info(session_id, info)

                if intent == "request_more_options":
                    more_options_count = info.get("more_options_count", 0)

                    if more_options_count >= 5:
                        return {
                            "reply": "I have already suggested more options 5 times. Please choose a slot, give another time, or cancel."
                        }

                    info["more_options_count"] = more_options_count + 1
                    info["slot_suggestion_offset"] = info.get("slot_suggestion_offset", 0) + 3

                    available_slots = get_available_slots(info)

                    chat_sessions[session_id] = {
                        "state": "create_conflict",
                        "info": info
                    }

                    return {
                        "reply": (
                            "Here are more available slots:\n\n"
                            f"{format_slots_for_chat(available_slots)}\n\n"
                            "You can choose a number, give another time, ask for more options, or say cancel."
                        )
                    }

                if intent == "provide_new_time":
                    original_title = info.get("event_title")
                    original_duration = info.get("duration_minutes", 30)
                    original_participants = info.get("participants", [])

                    info = update_scheduling_info(
                        info,
                        message,
                        "The requested time has a conflict. Update only the date, time, or timezone for the same event being created. Do not change the action_type to reschedule or delete."
                    )

                    # Keep this as a create flow because this is conflict resolution for a new event.
                    info["action_type"] = "create"

                    if not info.get("event_title"):
                        info["event_title"] = original_title

                    if not info.get("duration_minutes"):
                        info["duration_minutes"] = original_duration

                    if not info.get("participants"):
                        info["participants"] = original_participants

                    info = clean_participants(info)
                    info = fix_year_if_missing(message, info)

                    return handle_valid_agent_info(session_id, info)

                return {"reply": "I could not understand your response. Please choose a slot, give another time, ask for more options, or say cancel."}

            if state == "delete_choose":
                if message.lower() == "cancel":
                    chat_sessions.pop(session_id, None)
                    return {"reply": "Delete cancelled."}

                events = session["events"]
                info = session["info"]

                if message.isdigit():
                    choice_number = int(message)
                else:
                    choice_number = interpret_event_choice(message, events, info["timezone"])

                try:
                    choice_number = int(choice_number)
                except Exception:
                    return {"reply": "I could not understand which event you want to delete."}

                if choice_number < 1 or choice_number > len(events):
                    return {"reply": f"Invalid choice. I found only {len(events)} event(s)."}

                event_to_delete = events[choice_number - 1]
                title = event_to_delete.get("summary", "No Title")
                start_raw = event_to_delete["start"].get("dateTime", event_to_delete["start"].get("date"))
                start = format_event_time(start_raw, info["timezone"])

                chat_sessions[session_id] = {
                    "state": "delete_confirm",
                    "event": event_to_delete,
                    "info": info
                }

                return {"reply": f"Are you sure you want to delete '{title}' at {start}? Type yes or no."}

            if state == "delete_confirm":
                if message.lower() == "yes":
                    event_to_delete = session["event"]
                    delete_event_by_id(event_to_delete["id"])
                    chat_sessions.pop(session_id, None)
                    return {"reply": "Event deleted successfully."}

                if message.lower() == "no":
                    chat_sessions.pop(session_id, None)
                    return {"reply": "Delete cancelled."}

                return {"reply": "Please type yes or no."}

            if state == "reschedule_choose":
                if message.lower() == "cancel":
                    chat_sessions.pop(session_id, None)
                    return {"reply": "Reschedule cancelled."}

                events = session["events"]
                info = session["info"]

                if message.isdigit():
                    choice_number = int(message)
                else:
                    choice_number = interpret_event_choice(message, events, info["timezone"])

                try:
                    choice_number = int(choice_number)
                except Exception:
                    return {"reply": "I could not understand which event you want to reschedule."}

                if choice_number < 1 or choice_number > len(events):
                    return {"reply": f"Invalid choice. I found only {len(events)} event(s)."}

                event_to_reschedule = events[choice_number - 1]
                title = event_to_reschedule.get("summary", "No Title")

                chat_sessions[session_id] = {
                    "state": "reschedule_new_time",
                    "event": event_to_reschedule,
                    "info": info
                }

                return {"reply": f"What new date and time should I move '{title}' to?"}

            if state == "reschedule_new_time":
                event_to_reschedule = session["event"]
                info = session["info"]

                old_title = event_to_reschedule.get("summary", "No Title")

                new_info = {
                    "action_type": "create",
                    "event_title": old_title,
                    "date": None,
                    "time": None,
                    "timezone": info["timezone"],
                    "duration_minutes": info.get("duration_minutes", 30),
                    "participants": []
                }

                new_info = update_scheduling_info(
                    new_info,
                    message,
                    "The user is providing the new date, time, and timezone for rescheduling this event."
                )

                new_info = clean_participants(new_info)
                new_info = fix_year_if_missing(message, new_info)

                check_result = check_scheduling_info(new_info)

                if check_result[0] == False:
                    return {"reply": check_result[1]}

                has_conflict, conflicts = check_calendar_conflict(new_info)

                if has_conflict:
                    return {
                        "reply": (
                            "The new time has a conflict:\n\n"
                            f"{format_conflicts_for_chat(conflicts, new_info.get('timezone'))}\n\n"
                            "Please provide another date and time."
                        )
                    }

                old_start_raw = event_to_reschedule["start"].get("dateTime", event_to_reschedule["start"].get("date"))
                old_start = format_event_time(old_start_raw, info["timezone"])

                chat_sessions[session_id] = {
                    "state": "reschedule_confirm",
                    "event": event_to_reschedule,
                    "new_info": new_info,
                    "old_start": old_start
                }

                return {
                    "reply": (
                        f"Are you sure you want to reschedule '{old_title}' "
                        f"from {old_start} to {new_info.get('date')} at {new_info.get('time')} "
                        f"({new_info.get('timezone')})? Type yes or no."
                    )
                }

            if state == "reschedule_confirm":
                if message.lower() == "yes":
                    event_to_reschedule = session["event"]
                    new_info = session["new_info"]

                    updated_event = update_event_by_id(event_to_reschedule["id"], new_info)

                    chat_sessions.pop(session_id, None)

                    return {
                        "reply": (
                            "Event rescheduled successfully.\n\n"
                            f"Title: {new_info.get('event_title')}\n"
                            f"New date: {new_info.get('date')}\n"
                            f"New time: {new_info.get('time')}\n"
                            f"Timezone: {new_info.get('timezone')}\n"
                            # f"Calendar link: {updated_event.get('htmlLink')}"
                        )
                    }

                if message.lower() == "no":
                    chat_sessions.pop(session_id, None)
                    return {"reply": "Reschedule cancelled."}

                return {"reply": "Please type yes or no."}

        info = extract_scheduling_info(message)
        info = clean_participants(info)
        info = fix_year_if_missing(message, info)
        print("\n=== LLM EXTRACTION RESULT ===", flush=True)
        print(json.dumps(info, indent=2, ensure_ascii=False), flush=True)
        print("=============================\n", flush=True)
        ambiguous_time = get_ambiguous_hour_from_message(message)

        if ambiguous_time is not None:
            info["time"] = None

            chat_sessions[session_id] = {
                "state": "awaiting_ampm",
                "info": info,
                "ambiguous_hour": ambiguous_time["hour"],
                "ambiguous_minute": ambiguous_time["minute"]
            }

            return {
                "reply": "Do you mean AM or PM?"
            }

        check_result = check_scheduling_info(info)

        if check_result[0] == False:
            chat_sessions[session_id] = {
                "state": "awaiting_clarification",
                "info": info,
                "question": check_result[1]
            }

            return {"reply": check_result[1]}

        return handle_valid_agent_info(session_id, info)

    except Exception as error:
        return {
            "reply": f"I ran into an error while processing the request: {error}"
        }
    
#make user agent recognize am or pm...........

def get_ambiguous_hour_from_message(message):
    text = message.lower()

    clear_time_words = [
        "am", "pm", "a.m.", "p.m.",
        "morning", "afternoon", "evening", "night",
        "noon", "midnight"
    ]

    for word in clear_time_words:
        if word in text:
            return None

    pattern = r"\bat\s+(\d{1,2})(?::(\d{2}))?\s*(pst|pdt|pt|est|edt|et|kst|utc)?\b"
    match = re.search(pattern, text)

    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2)) if match.group(2) else 0

    if 1 <= hour <= 12:
        return {
            "hour": hour,
            "minute": minute
        }

    return None


def interpret_ampm_answer(message):
    text = message.lower().strip()

    if "pm" in text or "p.m." in text or "afternoon" in text or "evening" in text or "night" in text:
        return "PM"

    if "am" in text or "a.m." in text or "morning" in text:
        return "AM"

    if "noon" in text:
        return "PM"

    if "midnight" in text:
        return "AM"

    return None


def apply_ampm_to_info(info, hour, minute, ampm):
    if ampm == "PM" and hour != 12:
        hour += 12

    if ampm == "AM" and hour == 12:
        hour = 0

    info["time"] = f"{hour:02d}:{minute:02d}"
    return info

#we need to reset state if user request totally different equestion during the conversation 

# for example, After showing the delete list, if you immediately type "Reschedule..." and the agent switches to the reschedule flow instead of staying stuck in the old delete flow
def looks_like_new_top_level_request(message):
    text = message.lower().strip()

    # Follow-up answers should not reset the current flow.
    if text in ["yes", "no", "cancel", "actually cancel this", "never mind", "stop"]:
        return False

    if text.isdigit():
        return False

    # Conflict-resolution follow-ups should not reset the current flow.
    if text.startswith("i want to choose"):
        return False

    if text.startswith("want to choose"):
        return False

    if text.startswith("choose"):
        return False

    if text.startswith("can you show me more"):
        return False

    if text.startswith("show me more"):
        return False

    if text.startswith("more options"):
        return False

    # "Move it to..." is usually a follow-up in conflict or reschedule flows.
    if text.startswith("move it to"):
        return False

    # New create requests.
    if text.startswith("schedule "):
        return True

    if text.startswith("book "):
        return True

    if text.startswith("create "):
        return True

    if text.startswith("add "):
        return True

    # New reschedule requests.
    if text.startswith("reschedule "):
        return True

    if text.startswith("change my "):
        return True

    if text.startswith("move my "):
        return True

    # New delete requests.
    if text.startswith("can i delete"):
        return True

    if text.startswith("delete my "):
        return True

    if text.startswith("remove my "):
        return True

    if text.startswith("cancel my "):
        return True

    return False