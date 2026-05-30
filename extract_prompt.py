import os
import json
from dotenv import load_dotenv
from google import genai
from google_calendar_service import (
    check_calendar_conflict,
    create_event_from_info,
    print_conflicts,
    get_available_slots,
    delete_event_by_id,
    find_matching_events
)
from validation import check_scheduling_info
from timezone_setup import has_ambiguous_time
from manage_date import fix_year_if_missing
from datetime import datetime
from zoneinfo import ZoneInfo

load_dotenv()

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

SYSTEM_INSTRUCTION = """
You are a scheduling information extraction assistant.

Your job is to extract structured scheduling information from the user's prompt.

Return ONLY valid JSON.
Do not create, delete, or reschedule calendar events.
Do not assume a timezone if the user did not clearly provide one.

Required JSON fields:
{
  "action_type": "create | delete | reschedule | unknown",
  "event_title": string or null,
  "date": "YYYY-MM-DD" or null,
  "time": "HH:MM" or null,
  "timezone": string or null,
  "duration_minutes": integer or null,
  "participants": array of strings
}

Rules:
1. If the user asks to book, schedule, or create a meeting, action_type should be "create".
2. If the user asks to cancel or delete a meeting, action_type should be "delete".
3. If the user asks to move, change, or reschedule a meeting, action_type should be "reschedule".
4. If the user does not provide a timezone, timezone must be null.
5. Do not guess timezone.
6. If duration is missing, use 30.
7. If participants are missing, use an empty array.
8. If the date is ambiguous or missing, use null.
9. If the time is ambiguous or missing, use null.


10. If user does not provide AM or PM, do not assume it. 
11. When user provide date for the reservation, but didn't provide year, use the current year. If the date has already passed for the current year, use the next year. For example, if today is 2024-06-01 and the user says "Schedule a meeting on June 5th", then the date should be 2024-06-05. But if the user says "Schedule a meeting on May 30th", then the date should be 2025-05-30.
"""


# LLM taking care of user answer for "cancle"
# LLM handles the user's response after a conflict.
# It decides whether the user wants to cancel, choose a suggested slot, or provide another time.

def interpret_conflict_response(user_answer):
    # Use the LLM to understand what the user wants after a conflict.
    # Possible intents: cancel, choose a slot, provide a new time, or ask for more options.

    conflict_prompt = f"""
You are interpreting the user's response after a calendar scheduling conflict.

The user was shown suggested available slots and asked to choose a slot, give another time, ask for more options, or cancel.

User answer:
{user_answer}

Return ONLY valid JSON in this format:
{{
  "intent": "cancel | choose_slot | provide_new_time | request_more_options | unclear",
  "choice": 1 or 2 or 3 or null
}}

Rules:
- If the user wants to cancel, stop, never mind, or not create the event, intent should be "cancel".
- If the user chooses one of the suggested slots, intent should be "choose_slot".
- If the user chooses the first suggestion, choice should be 1.
- If the user chooses the second suggestion, choice should be 2.
- If the user chooses the third suggestion, choice should be 3.
- If the user provides a different date or time, intent should be "provide_new_time".
- If the user rejects the suggested slots or asks for different/more options, intent should be "request_more_options".
- If unclear, intent should be "unclear" and choice should be null.
- Do not guess.
"""

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=conflict_prompt,
    )

    raw_text = response.text.strip()

    if raw_text.startswith("```"):
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return {
            "intent": "unclear",
            "choice": None
        }


def extract_scheduling_info(user_prompt):
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=f"{SYSTEM_INSTRUCTION}\n\nUser prompt: {user_prompt}",
    )

    raw_text = response.text.strip()

    if raw_text.startswith("```"):
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return {
            "action_type": "unknown",
            "event_title": None,
            "date": None,
            "time": None,
            "timezone": None,
            "duration_minutes": None,
            "participants": [],
            "error": "Failed to parse LLM output",
            "raw_output": raw_text,
        }


# chage the even formate
def format_event_time(event_time_text, timezone):
    # Convert Google Calendar time text into readable local time.
    if not event_time_text:
        return "Unknown time"

    # All-day events may only have a date, not a full dateTime.
    if "T" not in event_time_text:
        return event_time_text

    event_time_text = event_time_text.replace("Z", "+00:00")

    event_time = datetime.fromisoformat(event_time_text)
    local_time = event_time.astimezone(ZoneInfo(timezone))

    return local_time.strftime("%I:%M %p %Z")

def interpret_delete_choice(user_answer, events, timezone):
    # Use the LLM to understand which listed event the user wants to delete.
    # The LLM sees the numbered event list and maps the user's answer to a choice.

    event_list_text = ""

    for index, event in enumerate(events):
        title = event.get("summary", "No Title")

        start_raw = event["start"].get("dateTime", event["start"].get("date"))
        end_raw = event["end"].get("dateTime", event["end"].get("date"))

        start = format_event_time(start_raw, timezone)
        end = format_event_time(end_raw, timezone)

        event_list_text += f"{index + 1}. {title}: {start} - {end}\n"

    delete_choice_prompt = f"""
You are interpreting which calendar event the user selected for deletion.

The user was shown this numbered list of events:
{event_list_text}

User answer:
{user_answer}

Return ONLY valid JSON in this format:
{{
  "choice": integer or null
}}

Rules:
- If the user clearly chooses one of the listed event numbers, return that number.
- If the user refers to an event by title, return the matching event number.
- If the user says "first", return 1.
- If the user says "second", return 2.
- If the user says "third", return 3.
- If the user does not clearly choose one event, return null.
- Do not guess.
"""

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=delete_choice_prompt,
    )

    raw_text = response.text.strip()

    if raw_text.startswith("```"):
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()

    try:
        result = json.loads(raw_text)
        return result.get("choice")
    except json.JSONDecodeError:
        return None

def update_scheduling_info(current_info, user_answer, question):

    update_prompt = f"""
You are updating missing scheduling information.

Current scheduling information:
{json.dumps(current_info, indent=2)}

The agent asked this question:
{question}

The user answered:
{user_answer}

Update the JSON using the user's answer.
Return ONLY valid JSON.
Keep existing values if they are already known.
Do not guess missing information.

Required JSON fields:
{{
  "action_type": "create | delete | reschedule | unknown",
  "event_title": string or null,
  "date": "YYYY-MM-DD" or null,
  "time": "HH:MM" or null,
  "timezone": string or null,
  "duration_minutes": integer or null,
  "participants": array of strings
}}
"""
    

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=update_prompt,
    )

    updated_text = response.text.strip()

    if updated_text.startswith("```"):
        updated_text = updated_text.replace("```json", "")
        updated_text = updated_text.replace("```", "")
        updated_text = updated_text.strip()

    try:
        return json.loads(updated_text)
    except json.JSONDecodeError:
        print("Failed to parse updated LLM output.")
        print(updated_text)
        return current_info


# Handle calendar conflicts.
# Shows suggested slots, lets the user cancel, choose a slot, or provide another time.
def handle_conflict(result, conflicts):
    print_conflicts(conflicts)

    available_slots = get_available_slots(result)

    print("\nSuggested available time slots:")
    for index, slot in enumerate(available_slots):
        start_time = slot[0]
        end_time = slot[1]

        print(
            f"{index + 1}. {start_time.strftime('%Y-%m-%d %I:%M %p')} - {end_time.strftime('%I:%M %p')}"
        )

    user_answer = input(
        "\nEnter a suggested number, another date/time, ask for more options, or type cancel: "
    )

    conflict_response = interpret_conflict_response(user_answer)

    intent = conflict_response.get("intent")
    choice_number = conflict_response.get("choice")

    if intent == "cancel":
        print("\nCancelled. I will not create the new event.")
        return result, True
    

    if intent == "choose_slot":
        if choice_number is None:
            print("\nInvalid slot number.")
            return result, False

        try:
            choice_number = int(choice_number)
        except ValueError:
            print("\nInvalid slot number.")
            return result, False

        if choice_number >= 1 and choice_number <= len(available_slots):
            selected_slot = available_slots[choice_number - 1]
            selected_start = selected_slot[0]

            result["date"] = selected_start.strftime("%Y-%m-%d")
            result["time"] = selected_start.strftime("%H:%M")

            print(
                f"\nSelected slot: {selected_start.strftime('%Y-%m-%d %I:%M %p')}"
            )

            return result, False

        print("\nInvalid slot number.")
        return result, False

    if intent == "request_more_options":
        # Limit repeated suggestion requests to avoid an infinite loop.
        more_options_count = result.get("more_options_count", 0)

        if more_options_count >= 5:   #show only 5 times.... 
            print("\nI have already suggested more options 5 times.")
            print("Please choose one of the suggested slots, provide another date/time, or say cancel.")
            return result, False

        result["more_options_count"] = more_options_count + 1

        # Move to the next group of suggested slots.
        result["slot_suggestion_offset"] = result.get("slot_suggestion_offset", 0) + len(available_slots)

        print("\nOkay, I will suggest different time slots.")

        return result, False

    if intent == "provide_new_time":
        result = update_scheduling_info(
            result,
            user_answer,
            "The requested time has a conflict. Update the event with the user's new date, time, or timezone."
        )

        result = fix_year_if_missing(user_answer, result)

        return result, False

    print("\nI could not understand your response.")
    print("Please choose one of the suggested slots, provide another date/time, ask for more options, or say cancel.")

    return result, False




if __name__ == "__main__":
    prompt = input("Enter scheduling request: ")

    if has_ambiguous_time(prompt):
        print("Do you mean AM or PM?")
        am_pm_answer = input("Your answer: ")
        prompt = prompt + " " + am_pm_answer

    result = extract_scheduling_info(prompt)
    result = fix_year_if_missing(prompt, result)

    while True:
        check_result = check_scheduling_info(result)

        is_valid = check_result[0]
        message = check_result[1]

        print("\nCurrent extracted information:")
        print(json.dumps(result, indent=2))

        print("\nValidation message:")
        print(message)

        if is_valid == True:
            action = result.get("action_type")

            # If there is a conflict, ask whether the user wants to try another time, for example if scheduled finishes at 3pm then get 3-4, 4-5. 5-6 slots
            if action == "create":
                print("\nReady to check calendar conflicts.")

                has_conflict, conflicts = check_calendar_conflict(result)

                if has_conflict == True:
                    # deal with the conflict 
                    result, should_break = handle_conflict(result, conflicts)

                    if should_break:
                        break

                    continue

                else:
                    try:
                        created_event = create_event_from_info(result)

                        print("\nEvent created successfully.")
                        print(f"Title: {result.get('event_title')}")
                        print(f"Date: {result.get('date')}")
                        print(f"Time: {result.get('time')}")
                        print(f"Timezone: {result.get('timezone')}")
                        print(f"Duration: {result.get('duration_minutes')} minutes")
                        print(f"Calendar link: {created_event.get('htmlLink')}")

                    except Exception as error:
                        print("\nI could not create the event because the Calendar API request failed.")
                        print("Please try again later.")
                        print(f"Error details: {error}")
                break 


            elif action == "delete":
                matching_events = find_matching_events(result)

                if len(matching_events) == 0:
                    print("\nI could not find any events on that date.")
                    break

                print(f"\nI found these event(s) on {result.get('date')} ({result.get('timezone')}):")

                for index, event in enumerate(matching_events):
                    title = event.get("summary", "No Title")

                    start_raw = event["start"].get("dateTime", event["start"].get("date"))
                    end_raw = event["end"].get("dateTime", event["end"].get("date"))

                    start = format_event_time(start_raw, result["timezone"])
                    end = format_event_time(end_raw, result["timezone"])

                    print(f"{index + 1}. {title}")
                    print(f"   Time: {start} - {end}")


                event_to_delete = None
                attempt_count = 0
                max_attempts = 3

                while event_to_delete is None and attempt_count < max_attempts:
                    choice = input(
                        "\nWhich event should I delete? You can enter a number, answer naturally, or type cancel: "
                    )

                    if choice.lower().strip() == "cancel":
                        print("\nDelete cancelled.")
                        break

                    attempt_count = attempt_count + 1

                    if choice.strip().isdigit():
                        choice_number = int(choice.strip())
                    else:
                        choice_number = interpret_delete_choice(
                            choice,
                            matching_events,
                            result["timezone"]
                        )

                    if choice_number is None:
                        print("\nI could not understand which event you want to delete.")
                        print("Please choose one of the listed events, or type cancel.")
                        continue

                    try:
                        choice_number = int(choice_number)
                    except ValueError:
                        print("\nInvalid choice.")
                        print("Please choose one of the listed events, or type cancel.")
                        continue

                    if choice_number < 1 or choice_number > len(matching_events):
                        print(f"\nInvalid choice. I found only {len(matching_events)} event(s).")
                        print(f"Please choose a number between 1 and {len(matching_events)}, or type cancel.")
                        continue

                    event_to_delete = matching_events[choice_number - 1]

                if event_to_delete is None:
                    if attempt_count >= max_attempts:
                        print("\nNumber of response attempts exceeded.")
                        print("Delete cancelled.")
                    break

              

                title = event_to_delete.get("summary", "No Title")
                start_raw = event_to_delete["start"].get("dateTime", event_to_delete["start"].get("date"))
                start = format_event_time(start_raw, result["timezone"])

                confirm = input(
                    f"\nAre you sure you want to delete '{title}' at {start}? Type exactly yes or no: "
                )

                if confirm.lower().strip() == "yes":
                    try:
                        delete_event_by_id(event_to_delete["id"])
                        print("\nEvent deleted successfully.")
                    except Exception as error:
                        print("\nI could not delete the event because the Calendar API request failed.")
                        print("Please try again later.")
                        print(f"Error details: {error}")

                elif confirm.lower().strip() == "no":
                    print("\nDelete cancelled.")

                else:
                    print("\nInvalid confirmation. Delete cancelled.")

                break

            elif action == "reschedule":
                print("\nReschedule flow is not implemented yet.")
                print("Next step: find the existing event, check the new time for conflicts, and ask for confirmation.")
                break

            else:
                print("\nUnsupported action type.")
                break

        user_answer = input("\nYour answer: ")

        if "time" in message.lower():
            if has_ambiguous_time(user_answer):
                print("Do you mean AM or PM?")
                am_pm_answer = input("Your answer: ")
                user_answer = user_answer + " " + am_pm_answer

        if "timezone" in message.lower():
            result["timezone"] = user_answer
        else:
            result = update_scheduling_info(result, user_answer, message)
            result = fix_year_if_missing(user_answer, result)