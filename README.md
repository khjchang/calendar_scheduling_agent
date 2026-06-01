## How to Run the Project

This project can be run in two ways:

```text
1. CLI agent mode
2. FastAPI tool endpoint mode
```

The CLI mode lets a user interact with the scheduling agent through the terminal.

The FastAPI mode exposes the calendar tools as HTTP endpoints for evaluation or external tool-calling.

---

## 1. Run the CLI Agent

### Step 1: Open the project folder

```bash
cd calendar-agent
```

### Step 2: Create and activate a virtual environment

If the virtual environment does not exist yet:

```bash
python3 -m venv venv
```

Activate it:

#### macOS / Linux

```bash
source venv/bin/activate
```

#### Windows

```bash
venv\Scripts\activate
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

If needed, install the main packages manually:

```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib google-genai python-dotenv fastapi uvicorn pydantic
```

### Step 4: Add required credentials

The project root should contain:

```text
.env
credentials.json
```

The `.env` file should contain:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

The `credentials.json` file should be downloaded from Google Cloud Console after enabling the Google Calendar API.

### Step 5: Authenticate Google Calendar

Run:

```bash
python quickstart.py
```

The first time this runs, a browser window will open and ask the user to log in with a Google account.

After authentication, a `token.json` file will be created automatically.

### Step 6: Run the agent

```bash
python extract_prompt.py
```

Example input:

```text
Schedule study meeting on August 10, 2026 at 3 PM PST for 1 hour
```

The agent will extract scheduling information, check for calendar conflicts, and create/delete/reschedule events depending on the user request.

---

## 2. Run the FastAPI Tool Endpoint Server

The FastAPI server exposes the backend calendar tools as HTTP endpoints.

### Step 1: Start the server

Make sure the virtual environment is activated:

```bash
source venv/bin/activate
```

Then run:

```bash
uvicorn app:app --reload
```

Expected output:

```text
Uvicorn running on http://127.0.0.1:8000
Application startup complete.
```

The server terminal should stay open while the API is running.

### Step 2: Open the API documentation

Open this URL in a browser:

```text
http://127.0.0.1:8000/docs
```

This opens the FastAPI interactive documentation page.

The OpenAPI schema is available at:

```text
http://127.0.0.1:8000/openapi.json
```

### Step 3: Available tool endpoint URLs

Local base URL:

```text
http://127.0.0.1:8000
```

Tool endpoints:

```text
POST http://127.0.0.1:8000/check_conflict
POST http://127.0.0.1:8000/get_available_slots
POST http://127.0.0.1:8000/create_event
POST http://127.0.0.1:8000/find_matching_events
POST http://127.0.0.1:8000/delete_event
POST http://127.0.0.1:8000/reschedule_event
```

---

## 3. Test the FastAPI Endpoints

Open a second terminal while the server is still running.

Activate the virtual environment:

```bash
source venv/bin/activate
```

### Test `create_event`

```bash
curl -X POST "http://127.0.0.1:8000/create_event" \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "create",
    "event_title": "API test meeting",
    "date": "2026-08-26",
    "time": "10:00",
    "timezone": "America/Los_Angeles",
    "duration_minutes": 30,
    "participants": []
  }'
```

Expected response:

```json
{
  "created": true,
  "event_id": "...",
  "html_link": "...",
  "summary": "API test meeting"
}
```

### Test `get_available_slots`

```bash
curl -X POST "http://127.0.0.1:8000/get_available_slots" \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "create",
    "event_title": "slot test",
    "date": "2026-08-26",
    "time": "10:00",
    "timezone": "America/Los_Angeles",
    "duration_minutes": 30,
    "participants": []
  }'
```

Expected response:

```json
{
  "available_slots": [
    {
      "start": "2026-08-26T09:00:00-07:00",
      "end": "2026-08-26T09:30:00-07:00"
    },
    {
      "start": "2026-08-26T13:00:00-07:00",
      "end": "2026-08-26T13:30:00-07:00"
    },
    {
      "start": "2026-08-26T15:00:00-07:00",
      "end": "2026-08-26T15:30:00-07:00"
    }
  ]
}
```

### Test `find_matching_events`

```bash
curl -X POST "http://127.0.0.1:8000/find_matching_events" \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "delete",
    "event_title": null,
    "date": "2026-08-26",
    "timezone": "America/Los_Angeles",
    "duration_minutes": 30,
    "participants": []
  }'
```

Expected response:

```json
{
  "events": [
    {
      "id": "...",
      "summary": "API test meeting",
      "start": {
        "dateTime": "...",
        "timeZone": "America/Los_Angeles"
      },
      "end": {
        "dateTime": "...",
        "timeZone": "America/Los_Angeles"
      },
      "html_link": "..."
    }
  ]
}
```

### Test `delete_event`

Use an event ID returned from `create_event` or `find_matching_events`.

```bash
curl -X POST "http://127.0.0.1:8000/delete_event" \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "PASTE_EVENT_ID_HERE"
  }'
```

Expected response:

```json
{
  "deleted": true,
  "event_id": "PASTE_EVENT_ID_HERE"
}
```

### Test `reschedule_event`

Use an existing event ID.

```bash
curl -X POST "http://127.0.0.1:8000/reschedule_event" \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "PASTE_EVENT_ID_HERE",
    "event_title": "API test meeting",
    "date": "2026-08-27",
    "time": "14:00",
    "timezone": "America/Los_Angeles",
    "duration_minutes": 30,
    "participants": []
  }'
```

Expected response:

```json
{
  "rescheduled": true,
  "event_id": "...",
  "html_link": "...",
  "summary": "API test meeting"
}
```

---

## 4. Notes for Evaluation

The FastAPI URLs above are local endpoints. They work when the evaluator runs the project locally.

If an externally accessible URL is required, the FastAPI app must be deployed to a hosting service such as Render, Railway, or another server platform.

For local evaluation, use:

```text
http://127.0.0.1:8000/docs
```

to inspect and test all available tool endpoints.
