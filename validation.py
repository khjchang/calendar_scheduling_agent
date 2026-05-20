from timezone_setup import SUPPORTED_TIMEZONES


def check_scheduling_info(info):
    action = info.get("action_type")

    if action == "unknown" or not action:
        return False, "I could not understand the calendar action. Do you want to create, delete, or reschedule an event?"

    if action == "create":
        if not info.get("event_title"):
            return False, "What should I call this event?"

        if not info.get("date"):
            return False, "What date should I schedule this event for?"

        if not info.get("time"):
            return False, "What time should I schedule this event for?"

        if not info.get("timezone"):
            return False, "Which timezone should I use?"

        if info.get("timezone") not in SUPPORTED_TIMEZONES:
            return False, f"I do not support the timezone '{info.get('timezone')}'. Please use other supported timezones."

        info["resolved_timezone"] = SUPPORTED_TIMEZONES[info.get("timezone")]

        if not info.get("duration_minutes"):
            info["duration_minutes"] = 30

        return True, "Scheduling information is complete."

    if action == "delete":
        if not info.get("event_title") and not info.get("date"):
            return False, "Which event do you want to delete?"

        return False, "I need to find the matching event first and ask for your confirmation before deleting it."

    if action == "reschedule":
        if not info.get("event_title"):
            return False, "Which event do you want to reschedule?"

        if not info.get("date"):
            return False, "What new date should I move it to?"

        if not info.get("time"):
            return False, "What new time should I move it to?"

        if not info.get("timezone"):
            return False, "Which timezone should I use for the new time?"

        return False, "I need to check for conflicts and ask for confirmation before rescheduling it."

    return False, "I could not process this request."