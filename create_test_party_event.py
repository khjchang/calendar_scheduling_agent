from quickstart import get_calendar_service


def create_party_event():
    service = get_calendar_service()

    event = {
        "summary": "Party Planning Meeting",
        "description": "Test event created by Calendar Scheduling Agent.",
        "start": {
            "dateTime": "2026-05-12T15:00:00-07:00",
            "timeZone": "America/Los_Angeles",
        },
        "end": {
            "dateTime": "2026-05-12T15:30:00-07:00",
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
    create_party_event()