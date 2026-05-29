import os
import json
from dotenv import load_dotenv
from google import genai
from google_calendar_service import (
    check_calendar_conflict,
    create_event_from_info,
    print_conflicts,
    get_available_slots,
    delete_event_by_id
)
from validation import check_scheduling_info
from timezone_setup import has_ambiguous_time
from manage_date import fix_year_if_missing

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
    conflict_prompt = f"""
You are interpreting the user's response after a calendar scheduling conflict.

The user was shown suggested available slots and asked to choose a slot, give another time, or cancel.

User answer:
{user_answer}

Return ONLY valid JSON in this format:
{{
  "intent": "cancel | choose_slot | provide_new_time | unclear",
  "choice": 1 or 2 or 3 or null
}}

Rules:
- If the user wants to cancel, stop, never mind, or not create the event, intent should be "cancel".
- If the user chooses one of the suggested slots, intent should be "choose_slot".
- If the user chooses the first suggestion, choice should be 1.
- If the user chooses the second suggestion, choice should be 2.
- If the user chooses the third suggestion, choice should be 3.
- If the user provides a different date or time, intent should be "provide_new_time".
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


# Add this function here
def user_wants_to_cancel(user_answer):
    cancel_prompt = f"""
Does the user want to cancel the current scheduling request?

User answer:
{user_answer}

Return ONLY valid JSON:
{{
  "cancel": true or false
}}

Rules:
- If the user wants to stop, cancel, never mind, or not create the event, return true.
- If the user is choosing another time or selecting a suggested slot, return false.
"""

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=cancel_prompt,
    )

    raw_text = response.text.strip()

    if raw_text.startswith("```"):
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()

    try:
        result = json.loads(raw_text)
        return result.get("cancel", False)
    except json.JSONDecodeError:
        return False





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
        "\nEnter a suggested number, another date/time, or type cancel: "
    )

    conflict_response = interpret_conflict_response(user_answer)

    intent = conflict_response.get("intent")
    choice_number = conflict_response.get("choice")

    if intent == "cancel":
        print("\nCancelled. I will not create the new event.")
        return result, True

    if intent == "choose_slot":
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

    if intent == "provide_new_time":
        result = update_scheduling_info(
            result,
            user_answer,
            "The requested time has a conflict. Update the event with the user's new date, time, or timezone."
        )

        result = fix_year_if_missing(user_answer, result)

        return result, False

    print("\nI could not understand your response.")
    print("Please choose one of the suggested slots, provide another date/time, or say cancel.")

    return result, False




# Convert a natural-language slot choice into 1, 2, 3, or None.
def interpret_slot_choice(user_answer):
    choice_prompt = f"""
You are interpreting which suggested calendar slot the user selected.

The user was shown 3 suggested slots:
1. First suggested slot
2. Second suggested slot
3. Third suggested slot

User answer:
{user_answer}

Return ONLY valid JSON in this format:
{{
  "choice": 1 | 2 | 3 | null
}}

Rules:
- If the user clearly chooses the first suggestion, return 1.
- If the user clearly chooses the second suggestion, return 2.
- If the user clearly chooses the third suggestion, return 3.
- If the user does not choose one of the suggestions, return null.
- Do not guess.
"""


    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=choice_prompt,
    )

    raw_text = response.text.strip()

    if raw_text.startswith("```"):
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()

    try:
        result = json.loads(raw_text)
        return result.get("choice")
    except json.JSONDecodeError:
        return None
    


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
                    created_event = create_event_from_info(result)
                    print("\nEvent created successfully.")
                    print(created_event.get("htmlLink"))

                break   


            elif action == "delete":
                print("\nDelete flow is not implemented yet.")
                print("Next step: find the matching event and ask for confirmation before deleting.")
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