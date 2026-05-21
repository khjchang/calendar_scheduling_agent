from datetime import datetime
import re


def user_provided_year(user_prompt):
    # Check if the user typed a 4-digit year like 2026 or 2027
    if re.search(r"\b20\d{2}\b", user_prompt):
        return True

    return False


def fix_year_if_missing(user_prompt, info):
    # If LLM did not extract a date, do nothing
    if not info.get("date"):
        return info

    # If the user already provided a year, keep the LLM's extracted year
    if user_provided_year(user_prompt):
        return info

    today = datetime.now()

    date_parts = info["date"].split("-")
    month = int(date_parts[1])
    day = int(date_parts[2])

    candidate_date = datetime(today.year, month, day)

    if candidate_date.date() < today.date():
        final_year = today.year + 1
    else:
        final_year = today.year

    info["date"] = f"{final_year}-{month:02d}-{day:02d}"

    return info