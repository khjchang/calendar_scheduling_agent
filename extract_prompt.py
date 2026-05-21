import os
import json
from dotenv import load_dotenv
from google import genai
from google_calendar_service import check_calendar_conflict, create_event_from_info, print_conflicts
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
            print("\nReady to check calendar conflicts.")

            has_conflict, conflicts = check_calendar_conflict(result)
            if has_conflict == True:
                     print_conflicts(conflicts)
                     print("\nI will not create the new event.")
            else:
                    created_event = create_event_from_info(result)
                    print("\nEvent created successfully.")
                    print(created_event.get("htmlLink"))
                    break

        user_answer = input("\nYour answer: ")

        if "time" in message.lower():
            if has_ambiguous_time(user_answer):
                print("Do you mean AM or PM?")
                am_pm_answer = input("Your answer: ")
                user_answer = user_answer + " " + am_pm_answer

        result = update_scheduling_info(result, user_answer, message)
        result = fix_year_if_missing(user_answer, result)