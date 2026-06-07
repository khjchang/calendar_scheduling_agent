# Calendar Scheduling Agent

This project is a Calendar Scheduling Agent that uses Gemini for natural-language understanding and the Google Calendar API for real calendar operations. The backend is implemented with FastAPI, and a simple chat-style frontend is provided for demo use.

## Required Files

Before running the project, the project root must include:

.env
credentials.json

The `.env` file should contain:

GEMINI_API_KEY=your_gemini_api_key_here

`credentials.json` should be downloaded from Google Cloud Console after enabling the Google Calendar API.

Do not include `.env`, `credentials.json`, or `token.json` in the submitted public zip.

## Setup

Create and activate a virtual environment:

python3 -m venv venv
source venv/bin/activate

Install dependencies:

python -m pip install -r requirements.txt

Authenticate Google Calendar:

python quickstart.py

This will open a browser for Google login and create `token.json`.

## Run Backend

Start the FastAPI server:

python -m uvicorn app:app --reload

Backend API documentation:

http://127.0.0.1:8000/docs

OpenAPI schema:

http://127.0.0.1:8000/openapi.json

## Run Frontend

Open a second terminal:

cd frontend
python3 -m http.server 3000

Then open:

http://127.0.0.1:3000

## Main API Endpoints

POST /check_conflict
POST /get_available_slots
POST /create_event
POST /find_matching_events
POST /delete_event
POST /reschedule_event
POST /agent_chat

## CLI Mode

The project can also be run through the terminal:

python extract_prompt.py

Example request:

Schedule study meeting on August 10, 2026 at 3 PM PST for 1 hour

## Notes

The project uses local endpoints by default. For local evaluation, run the backend and open:

http://127.0.0.1:8000/docs

The frontend demo runs at:

http://127.0.0.1:3000