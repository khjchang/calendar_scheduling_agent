import re


SUPPORTED_TIMEZONES = {
    "PT": "America/Los_Angeles",
    "pt": "America/Los_Angeles",
    "PST": "America/Los_Angeles",
    "pst": "America/Los_Angeles",
    "PDT": "America/Los_Angeles",
    "pdt": "America/Los_Angeles",

    "ET": "America/New_York",
    "et": "America/New_York",
    "EST": "America/New_York",
    "est": "America/New_York",
    "EDT": "America/New_York",
    "edt": "America/New_York",

    "KST": "Asia/Seoul",
    "kst": "Asia/Seoul",

    "GMT": "Europe/London",
    "gmt": "Europe/London",
    "BST": "Europe/London",
    "bst": "Europe/London",

    "UTC": "UTC",
    "utc": "UTC"
}

def has_ambiguous_time(user_text):
    text = user_text.lower().strip()
    # If AM or PM is included, the time is clear
    if "am" in text or "pm" in text:
        return False
    # If 24-hour time is used, it is clear  # Examples: 13:00, 14:30, 23:59
    if re.search(r"\b(1[3-9]|2[0-3]):[0-5][0-9]\b", text):
        return False
    # Ambiguous time after the word "at"  # for Examples: "at 3", "at 3:30", "at 2 pst"
    if re.search(r"\bat\s+([1-9]|1[0-2])(:[0-5][0-9])?\b", text):
        return True
    # If the user only typed a time as a follow-up answer # Examples: "3", "3:30", "2 pst"
    if re.fullmatch(r"([1-9]|1[0-2])(:[0-5][0-9])?", text):
        return True

    return False



def normalize_timezone(timezone_value):
    if timezone_value is None:
        return None

    if timezone_value in SUPPORTED_TIMEZONES:
        return SUPPORTED_TIMEZONES[timezone_value]

    if timezone_value in SUPPORTED_TIMEZONES.values():
        return timezone_value

    return None