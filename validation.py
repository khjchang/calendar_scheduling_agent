from timezone_setup import normalize_timezone


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

        normalized_timezone = normalize_timezone(info.get("timezone"))

        if not normalized_timezone:
             return False, f"I do not support the timezone '{info.get('timezone')}'. Please use a supported timezone."

        info["timezone"] = normalized_timezone

        if not info.get("duration_minutes"):
            info["duration_minutes"] = 30

        return True, "Scheduling information is complete."

    if action == "delete":
        if not info.get("date"):
            return False, "What date is the event on?"

        if not info.get("timezone"):
            # For delete requests, use the user's default calendar timezone.
            # This is safe because the user will choose from a list before deletion.
            info["timezone"] = "America/Los_Angeles"
        else:
            normalized_timezone = normalize_timezone(info.get("timezone"))

            if not normalized_timezone:
                return False, f"I do not support the timezone '{info.get('timezone')}'. Please use a supported timezone."

            info["timezone"] = normalized_timezone

        return True, "Ready to find events on that date before deleting."

    if action == "reschedule":
        # For rescheduling, first find the existing event.
        # We only need the original event date at this stage.
        # The new date/time will be collected later after the user selects an event.

        if not info.get("date"):
            return False, "What date is the event you want to reschedule?"

        if not info.get("timezone"):
            # Use the default calendar timezone for finding existing events.
            # This is safe because the user will select from a visible event list.
            #
            #
            # hum ..  .need to fix to  IANA timezone... otherwize google calendar api formate will have  problem . . . . fix it toward 
            info["timezone"] = "America/Los_Angeles"
        else:
            normalized_timezone = normalize_timezone(info.get("timezone"))

            if not normalized_timezone:
                return False, f"I do not support the timezone '{info.get('timezone')}'. Please use a supported timezone."

            info["timezone"] = normalized_timezone

        if not info.get("duration_minutes"):
            info["duration_minutes"] = 30

        return True, "Ready to find events on that date before rescheduling."

    return False, "I could not process this request."