from typing import List, Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException

from google_calendar_service import (
    check_calendar_conflict,
    create_event_from_info,
    get_available_slots,
    delete_event_by_id,
    update_event_by_id,
    find_matching_events
)

app = FastAPI(title="Calendar Scheduling Agent Tool API")


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


@app.get("/")
def root():
    return {
        "message": "Calendar Scheduling Agent Tool API is running.",
        "endpoints": [
            "/get_available_slots",
            "/create_event",
            "/delete_event",
            "/reschedule_event",
            "/find_matching_events",
            "/check_conflict"
        ]
    }


@app.post("/check_conflict")
def check_conflict(info: CalendarEventInfo):
    try:
        data = info.model_dump()
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
        data = info.model_dump()
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
        data = info.model_dump()

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
        data = info.model_dump()
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
        data = request.model_dump()
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