from quickstart import get_calendar_service


def create_test_event():
    service = get_calendar_service()

    event = {
        "summary": "Calendar Agent Test Meeting",
        "description": "Test event created by Calendar Scheduling Agent.",
        "start": {
            "dateTime": "2026-05-08T15:00:00-07:00",
            "timeZone": "America/Los_Angeles",
        },
        "end": {
            "dateTime": "2026-05-08T15:30:00-07:00",
            "timeZone": "America/Los_Angeles",
        },
    }

    created_event = service.events().insert(
        calendarId="primary",
        body=event
    ).execute()

    print("Event created successfully.")
    print(created_event.get("htmlLink"))


if __name__ == "__main__":
    create_test_event()
