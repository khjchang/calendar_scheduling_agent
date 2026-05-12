import os
import json
from dotenv import load_dotenv
from google import genai

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
"""


SUPPORTED_TIMEZONES = {
    # United States - Pacific Time
    "PT": "America/Los_Angeles",
    "pt": "America/Los_Angeles",
    "PST": "America/Los_Angeles",
    "pst": "America/Los_Angeles",
    "PDT": "America/Los_Angeles",
    "pdt": "America/Los_Angeles",
    "Pacific Time": "America/Los_Angeles",
    "pacific time": "America/Los_Angeles",
    "California": "America/Los_Angeles",
    "california": "America/Los_Angeles",
    "Los Angeles": "America/Los_Angeles",
    "los angeles": "America/Los_Angeles",

    # United States - Mountain Time
    "MT": "America/Denver",
    "mt": "America/Denver",
    "MST": "America/Denver",
    "mst": "America/Denver",
    "MDT": "America/Denver",
    "mdt": "America/Denver",
    "Mountain Time": "America/Denver",
    "mountain time": "America/Denver",
    "Denver": "America/Denver",
    "denver": "America/Denver",

    # United States - Central Time
    "CT": "America/Chicago",
    "ct": "America/Chicago",
    "CST": "America/Chicago",
    "cst": "America/Chicago",
    "CDT": "America/Chicago",
    "cdt": "America/Chicago",
    "Central Time": "America/Chicago",
    "central time": "America/Chicago",
    "Chicago": "America/Chicago",
    "chicago": "America/Chicago",

    # United States - Eastern Time
    "ET": "America/New_York",
    "et": "America/New_York",
    "EST": "America/New_York",
    "est": "America/New_York",
    "EDT": "America/New_York",
    "edt": "America/New_York",
    "Eastern Time": "America/New_York",
    "eastern time": "America/New_York",
    "New York": "America/New_York",
    "new york": "America/New_York",

    # Asia - Korea
    "KST": "Asia/Seoul",
    "kst": "Asia/Seoul",
    "Korea Time": "Asia/Seoul",
    "korea time": "Asia/Seoul",
    "Seoul": "Asia/Seoul",
    "seoul": "Asia/Seoul",

    # Asia - Japan
    "JST": "Asia/Tokyo",
    "jst": "Asia/Tokyo",
    "Japan Time": "Asia/Tokyo",
    "japan time": "Asia/Tokyo",
    "Tokyo": "Asia/Tokyo",
    "tokyo": "Asia/Tokyo",

    # Asia - China
    "CST China": "Asia/Shanghai",
    "cst china": "Asia/Shanghai",
    "China Time": "Asia/Shanghai",
    "china time": "Asia/Shanghai",
    "Shanghai": "Asia/Shanghai",
    "shanghai": "Asia/Shanghai",
    "Beijing": "Asia/Shanghai",
    "beijing": "Asia/Shanghai",

    # Asia - India
    "IST India": "Asia/Kolkata",
    "ist india": "Asia/Kolkata",
    "India Time": "Asia/Kolkata",
    "india time": "Asia/Kolkata",
    "New Delhi": "Asia/Kolkata",
    "new delhi": "Asia/Kolkata",
    "Mumbai": "Asia/Kolkata",
    "mumbai": "Asia/Kolkata",

    # Europe - United Kingdom
    "GMT": "Europe/London",
    "gmt": "Europe/London",
    "BST": "Europe/London",
    "bst": "Europe/London",
    "UK Time": "Europe/London",
    "uk time": "Europe/London",
    "London": "Europe/London",
    "london": "Europe/London",

    # Europe - Central Europe
    "CET": "Europe/Paris",
    "cet": "Europe/Paris",
    "CEST": "Europe/Paris",
    "cest": "Europe/Paris",
    "Central European Time": "Europe/Paris",
    "central european time": "Europe/Paris",
    "Paris": "Europe/Paris",
    "paris": "Europe/Paris",
    "Berlin": "Europe/Berlin",
    "berlin": "Europe/Berlin",

    # UTC
    "UTC": "UTC",
    "utc": "UTC"
}

def extract_scheduling_info(user_prompt: str) -> dict:
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


def check_scheduling_info(info: dict):
    # info  = llm json output
    # action_type, event_title, date, time, timezone, duration_minutes

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

        if not info.get("duration_minutes"):
            info["duration_minutes"] = 30

        return True, "I have added the event to your calendar."

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


    # if user give a prompt again based on validation message, we need to update which means we need to add extra information, from the existing info with new user answer and question, then check again until we have all the required info.

def update_scheduling_info(current_info, user_answer, question):
    # update_prompt is a variable that stores the prompt text that will be sent to Gemini.
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
        updated_info = json.loads(updated_text)
        return updated_info

    except json.JSONDecodeError:
        print("Failed to parse updated LLM output.")
        print(updated_text)
        return current_info
    

# only run on this py file 
if __name__ == "__main__":
    prompt = input("Enter scheduling request: ")

    result = extract_scheduling_info(prompt)

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
            break

        user_answer = input("\nYour answer: ")

        # This is the current JSON.
        # I asked for the time.
        # The user answered 3pm.
        # Keep the existing values and update only the missing field.
        result = update_scheduling_info(result, user_answer, message)