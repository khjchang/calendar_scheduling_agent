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
    text = user_text.lower()

    if "am" in text or "pm" in text:
        return False

    match = re.search(r"\b(\d{1,2}):(\d{2})\b", text)

    if match:
        hour = int(match.group(1))

        if 1 <= hour <= 12:
            return True

    return False