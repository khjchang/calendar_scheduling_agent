# Tool Endpoint Definitions

This project exposes backend calendar tools through FastAPI endpoints.

Local base URL:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

OpenAPI schema:

```text
http://127.0.0.1:8000/openapi.json
```

---

## 1. Check Conflict

### Endpoint

```text
POST /check_conflict
```

### Full Local URL

```text
http://127.0.0.1:8000/check_conflict
```

### Description

Checks whether a requested event time conflicts with existing events on the user's Google Calendar.

### Request Body

```json
{
  "action_type": "create",
  "event_title": "string",
  "date": "YYYY-MM-DD",
  "time": "HH:MM",
  "timezone": "IANA timezone string",
  "duration_minutes": 30,
  "participants": []
}
```

### Parameters

| Field            | Type             | Required | Description                                  |
| ---------------- | ---------------- | -------: | -------------------------------------------- |
| action_type      | string           | optional | Usually `"create"`                           |
| event_title      | string           | optional | Title of the event                           |
| date             | string           |      yes | Event date in `YYYY-MM-DD` format            |
| time             | string           |      yes | Event start time in `HH:MM` 24-hour format   |
| timezone         | string           |      yes | IANA timezone, such as `America/Los_Angeles` |
| duration_minutes | integer          | optional | Event duration in minutes                    |
| participants     | array of strings | optional | Participant email addresses                  |

### Response

```json
{
  "has_conflict": true,
  "conflicts": []
}
```

---

## 2. Get Available Slots

### Endpoint

```text
POST /get_available_slots
```

### Full Local URL

```text
http://127.0.0.1:8000/get_available_slots
```

### Description

Returns suggested available time slots near the requested date and time.

### Request Body

```json
{
  "action_type": "create",
  "event_title": "slot test",
  "date": "2026-08-26",
  "time": "10:00",
  "timezone": "America/Los_Angeles",
  "duration_minutes": 30,
  "participants": []
}
```

### Parameters

| Field            | Type             | Required | Description                 |
| ---------------- | ---------------- | -------: | --------------------------- |
| action_type      | string           | optional | Usually `"create"`          |
| event_title      | string           | optional | Event title                 |
| date             | string           |      yes | Requested date              |
| time             | string           |      yes | Requested start time        |
| timezone         | string           |      yes | IANA timezone               |
| duration_minutes | integer          | optional | Duration of the meeting     |
| participants     | array of strings | optional | Participant email addresses |

### Response

```json
{
  "available_slots": [
    {
      "start": "2026-08-26T09:00:00-07:00",
      "end": "2026-08-26T09:30:00-07:00"
    },
    {
      "start": "2026-08-26T13:00:00-07:00",
      "end": "2026-08-26T13:30:00-07:00"
    },
    {
      "start": "2026-08-26T15:00:00-07:00",
      "end": "2026-08-26T15:30:00-07:00"
    }
  ]
}
```

---

## 3. Create Event

### Endpoint

```text
POST /create_event
```

### Full Local URL

```text
http://127.0.0.1:8000/create_event
```

### Description

Creates a Google Calendar event after checking for conflicts. If a conflict exists, the event is not created.

### Request Body

```json
{
  "action_type": "create",
  "event_title": "API test meeting",
  "date": "2026-08-26",
  "time": "10:00",
  "timezone": "America/Los_Angeles",
  "duration_minutes": 30,
  "participants": []
}
```

### Parameters

| Field            | Type             | Required | Description                       |
| ---------------- | ---------------- | -------: | --------------------------------- |
| action_type      | string           | optional | `"create"`                        |
| event_title      | string           |      yes | Calendar event title              |
| date             | string           |      yes | Event date                        |
| time             | string           |      yes | Event start time                  |
| timezone         | string           |      yes | IANA timezone                     |
| duration_minutes | integer          | optional | Event duration                    |
| participants     | array of strings | optional | Valid participant email addresses |

### Response When Created

```json
{
  "created": true,
  "event_id": "6d9iv91pb94ldef56tv94sfvmc",
  "html_link": "https://www.google.com/calendar/event?...",
  "summary": "API test meeting"
}
```

### Response When Conflict Exists

```json
{
  "created": false,
  "reason": "conflict_detected",
  "conflicts": []
}
```

---

## 4. Find Matching Events

### Endpoint

```text
POST /find_matching_events
```

### Full Local URL

```text
http://127.0.0.1:8000/find_matching_events
```

### Description

Finds events on a requested date. If an event title is provided, it returns matching events. If no title is provided, it returns all events on that date.

This endpoint is used before delete and reschedule operations so the user can select the correct event.

### Request Body

```json
{
  "action_type": "delete",
  "event_title": null,
  "date": "2026-08-26",
  "timezone": "America/Los_Angeles",
  "duration_minutes": 30,
  "participants": []
}
```

### Parameters

| Field            | Type             | Required | Description                  |
| ---------------- | ---------------- | -------: | ---------------------------- |
| action_type      | string           | optional | `"delete"` or `"reschedule"` |
| event_title      | string or null   | optional | Event title to search for    |
| date             | string           |      yes | Date to search               |
| timezone         | string           |      yes | IANA timezone                |
| duration_minutes | integer          | optional | Not required for search      |
| participants     | array of strings | optional | Not required for search      |

### Response

```json
{
  "events": [
    {
      "id": "event_id_here",
      "summary": "API test meeting",
      "start": {
        "dateTime": "2026-08-26T10:00:00-07:00",
        "timeZone": "America/Los_Angeles"
      },
      "end": {
        "dateTime": "2026-08-26T10:30:00-07:00",
        "timeZone": "America/Los_Angeles"
      },
      "html_link": "https://www.google.com/calendar/event?..."
    }
  ]
}
```

---

## 5. Delete Event

### Endpoint

```text
POST /delete_event
```

### Full Local URL

```text
http://127.0.0.1:8000/delete_event
```

### Description

Deletes an existing Google Calendar event by event ID.

The agent should first call `/find_matching_events`, show the user the matching event list, ask the user to choose an event, and ask for confirmation before calling this endpoint.

### Request Body

```json
{
  "event_id": "PASTE_EVENT_ID_HERE"
}
```

### Parameters

| Field    | Type   | Required | Description              |
| -------- | ------ | -------: | ------------------------ |
| event_id | string |      yes | Google Calendar event ID |

### Response

```json
{
  "deleted": true,
  "event_id": "PASTE_EVENT_ID_HERE"
}
```

---

## 6. Reschedule Event

### Endpoint

```text
POST /reschedule_event
```

### Full Local URL

```text
http://127.0.0.1:8000/reschedule_event
```

### Description

Reschedules an existing Google Calendar event by event ID.

The agent should first call `/find_matching_events`, show the user the matching event list, ask the user to select the event, ask for the new date and time, check for conflicts, and ask for confirmation before calling this endpoint.

### Request Body

```json
{
  "event_id": "PASTE_EVENT_ID_HERE",
  "event_title": "API test meeting",
  "date": "2026-08-27",
  "time": "14:00",
  "timezone": "America/Los_Angeles",
  "duration_minutes": 30,
  "participants": []
}
```

### Parameters

| Field            | Type             | Required | Description                       |
| ---------------- | ---------------- | -------: | --------------------------------- |
| event_id         | string           |      yes | Google Calendar event ID          |
| event_title      | string           |      yes | Updated event title               |
| date             | string           |      yes | New event date                    |
| time             | string           |      yes | New start time                    |
| timezone         | string           |      yes | IANA timezone                     |
| duration_minutes | integer          | optional | New event duration                |
| participants     | array of strings | optional | Valid participant email addresses |

### Response When Rescheduled

```json
{
  "rescheduled": true,
  "event_id": "event_id_here",
  "html_link": "https://www.google.com/calendar/event?...",
  "summary": "API test meeting"
}
```

### Response When Conflict Exists

```json
{
  "rescheduled": false,
  "reason": "conflict_detected",
  "conflicts": []
}
```

---

# Tool Summary

| Tool                 | Endpoint                     | Purpose                                                                 |
| -------------------- | ---------------------------- | ----------------------------------------------------------------------- |
| Check Conflict       | `POST /check_conflict`       | Checks whether a requested time conflicts with existing calendar events |
| Get Available Slots  | `POST /get_available_slots`  | Suggests available time slots                                           |
| Create Event         | `POST /create_event`         | Creates a Google Calendar event                                         |
| Find Matching Events | `POST /find_matching_events` | Finds events before delete or reschedule                                |
| Delete Event         | `POST /delete_event`         | Deletes an event by event ID                                            |
| Reschedule Event     | `POST /reschedule_event`     | Updates an event to a new date and time                                 |

