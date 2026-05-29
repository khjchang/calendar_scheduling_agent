# Calendar Scheduling Agent

## Overview

This project is a Calendar Scheduling Agent built for Project 3 in the Agent Development course.

The agent helps users schedule calendar events using natural language. It uses an LLM to understand the user's request and a backend connected to Google Calendar API to check availability, detect conflicts, suggest alternative slots, and create calendar events.

The main design principle is:

```text
LLM = understands natural language and user intent
Backend = validates data, checks calendar availability, and performs real calendar actions
```

The system does not allow the LLM to directly create, delete, or reschedule calendar events. Calendar actions are only performed by backend functions after validation and conflict checking.

---

## Features

Current implemented features:

* Natural-language scheduling request parsing
* Structured JSON extraction using Gemini
* Validation for missing event title, date, time, timezone, and duration
* Timezone normalization
* AM/PM ambiguity detection
* Missing year correction
* Google Calendar API integration
* Conflict detection before event creation
* Alternative slot suggestion after conflicts
* Natural-language conflict response handling
* Real event creation in Google Calendar

Partially implemented or planned features:

* Full delete event flow
* Full reschedule event flow
* Multi-participant availability checking
* More advanced available-slot search
* Robust DST edge case handling
* Stronger API error handling

---

## Project Structure

```text
calendar-agent/
│
├── extract_prompt.py
├── quickstart.py
├── google_calendar_service.py
├── validation.py
├── timezone_setup.py
├── manage_date.py
├── requirements.txt
├── README.md
├── .env
├── credentials.json
├── token.json
└── venv/
```

### File Descriptions

#### `extract_prompt.py`

Main program file.

Responsibilities:

* Takes the user's scheduling request
* Calls Gemini to extract structured scheduling information
* Handles follow-up clarification
* Runs validation
* Checks calendar conflicts
* Handles suggested slot selection
* Creates events when safe

#### `quickstart.py`

Handles Google Calendar authentication.

Responsibilities:

* Runs OAuth 2.0 authentication
* Loads and refreshes Google Calendar credentials
* Creates the Google Calendar service object

#### `google_calendar_service.py`

Contains Google Calendar helper functions.

Responsibilities:

* Build start and end datetimes
* Check calendar conflicts
* Create calendar events
* Suggest available slots
* Print conflict information

#### `validation.py`

Validates extracted scheduling information.

Responsibilities:

* Check missing required fields
* Normalize timezone
* Decide whether the request is ready for calendar execution

#### `timezone_setup.py`

Handles timezone logic.

Responsibilities:

* Convert timezone aliases to IANA timezone names
* Detect ambiguous time inputs

Examples:

```text
PST → America/Los_Angeles
PT → America/Los_Angeles
ET → America/New_York
KST → Asia/Seoul
```

#### `manage_date.py`

Handles dates without a year.

Rule:

```text
If the user provides a month and day but no year, use the current year.
If that date has already passed, use next year.
```

---

## Requirements

This project requires:

* Python 3.9 or higher
* Google Calendar API credentials
* Gemini API key
* A Google account with Calendar access

Recommended Python version:

```text
Python 3.10+
```

Python 3.9 may work, but some packages may show end-of-life warnings.

---

## Setup Instructions

### 1. Clone or Download the Project

```bash
git clone <your-repository-url>
cd calendar-agent
```

Or download the project folder manually and open it in a terminal.

---

### 2. Create a Virtual Environment

```bash
python3 -m venv venv
```

Activate the virtual environment:

#### macOS / Linux

```bash
source venv/bin/activate
```

#### Windows

```bash
venv\Scripts\activate
```

---

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

If `requirements.txt` is not available, install the required packages manually:

```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib google-genai python-dotenv
```

---

### 4. Set Up Google Calendar API

1. Go to Google Cloud Console.
2. Create a new project.
3. Enable the Google Calendar API.
4. Configure the OAuth consent screen.
5. Create an OAuth Client ID.
6. Choose Desktop App as the application type.
7. Download the OAuth credentials file.
8. Rename the downloaded file to:

```text
credentials.json
```

9. Place `credentials.json` in the project root folder.

The project root should look like this:

```text
calendar-agent/
├── credentials.json
├── quickstart.py
├── extract_prompt.py
└── ...
```

---

### 5. Set Up Gemini API Key

Create a `.env` file in the project root folder.

```bash
touch .env
```

Add your Gemini API key:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

Do not share this file publicly.

---

### 6. Authenticate Google Calendar

Run:

```bash
python quickstart.py
```

The first time you run this, a browser window will open and ask you to log in with your Google account.

After successful authentication, a `token.json` file will be created automatically.

---

### 7. Run the Calendar Scheduling Agent

Run:

```bash
python extract_prompt.py
```

Then enter a scheduling request.

Example:

```text
Schedule study meeting on July 21, 2026 at 3 PM PST for 1 hour
```

---

## Example Usage

### Example 1: Create an Event

User input:

```text
Schedule study meeting on July 21, 2026 at 3 PM PST for 1 hour
```

Expected behavior:

```text
Current extracted information:
{
  "action_type": "create",
  "event_title": "study meeting",
  "date": "2026-07-21",
  "time": "15:00",
  "timezone": "America/Los_Angeles",
  "duration_minutes": 60,
  "participants": []
}

Validation message:
Scheduling information is complete.

Ready to check calendar conflicts.

Event created successfully.
```

---

### Example 2: Conflict Detection

If the user already has an event at the requested time, the system detects the conflict.

User input:

```text
Schedule basketball practice on July 21, 2026 at 3 PM PST for 1 hour
```

Expected behavior:

```text
Conflict detected. You already have event(s) at this time:
- study meeting: 2026-07-21T15:00:00-07:00 to 2026-07-21T16:00:00-07:00

Suggested available time slots:
1. 2026-07-21 04:00 PM - 05:00 PM
2. 2026-07-21 05:00 PM - 06:00 PM
3. 2026-07-21 06:00 PM - 07:00 PM
```

The user can choose a suggested slot:

```text
I want to choose 3
```

Expected behavior:

```text
Selected slot: 2026-07-21 06:00 PM

Event created successfully.
```

---

### Example 3: Cancel After Conflict

User input after conflict:

```text
Actually I want to cancel this
```

Expected behavior:

```text
Cancelled. I will not create the new event.
```

---

### Example 4: Missing Timezone

User input:

```text
Schedule office hour on July 24, 2026 at 2 PM for 30 minutes
```

Expected behavior:

```text
Which timezone should I use?
```

User answer:

```text
PST
```

Expected behavior:

```text
timezone = America/Los_Angeles
```

---

### Example 5: Ambiguous AM/PM

User input:

```text
Schedule dentist appointment on July 25, 2026 at 3 PST for 1 hour
```

Expected behavior:

```text
Do you mean AM or PM?
```

User answer:

```text
PM
```

Expected behavior:

```text
time = 15:00
```

---

## Current Agent Flow

```text
User request
→ Gemini extracts structured scheduling information
→ Validation checks missing fields
→ Timezone is normalized
→ Missing year is corrected
→ Google Calendar conflict check runs
→ If no conflict, create event
→ If conflict, suggest alternative slots
→ User selects a slot, provides another time, or cancels
→ Selected time is checked again
→ Event is created only after conflict check passes
```

---

## Environment Variables

The project uses the following environment variable:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

This should be stored in a `.env` file.

---

## Files Not to Commit or Submit Publicly

Do not commit or submit these files:

```text
.env
credentials.json
token.json
venv/
__pycache__/
```

These files may contain private credentials, tokens, or local environment data.

Recommended `.gitignore`:

```gitignore
.env
credentials.json
token.json
venv/
__pycache__/
*.pyc
.DS_Store
```

---

