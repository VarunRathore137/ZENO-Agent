"""
Google Calendar, Gmail, and Tasks integration via OAuth 2.0.

Setup:
  1. Go to https://console.cloud.google.com/ → Create Project
  2. Enable APIs: Calendar API, Gmail API, Google Tasks API
  3. Create OAuth 2.0 credentials (Desktop application type)
  4. Download credentials.json
  5. Place at: ~/.elysia/google_oauth/credentials.json
  6. First tool call will open a browser for OAuth consent
  7. Token saved to ~/.elysia/google_oauth/token.json (auto-refreshed)
"""

from __future__ import annotations

import json
import os
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

from ..registry import ToolError, register

# ---------------------------------------------------------------------------
# OAuth helpers
# ---------------------------------------------------------------------------

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/tasks",
]

def _resolve_oauth_dir() -> Path:
    """Resolve the directory holding credentials.json and token.pickle."""
    zeno_dir = Path.home() / "Zeno" / "google_oauth"
    dot_zeno_dir = Path.home() / ".zeno" / "google_oauth"
    dot_elysia_dir = Path.home() / ".elysia" / "google_oauth"

    if (zeno_dir / "credentials.json").exists():
        return zeno_dir
    if (dot_zeno_dir / "credentials.json").exists():
        return dot_zeno_dir
    if (dot_elysia_dir / "credentials.json").exists():
        return dot_elysia_dir

    # Default to ~/Zeno/google_oauth
    zeno_dir.mkdir(parents=True, exist_ok=True)
    return zeno_dir


_OAUTH_DIR = _resolve_oauth_dir()
_CREDENTIALS_PATH = _OAUTH_DIR / "credentials.json"
_TOKEN_PATH = _OAUTH_DIR / "token.pickle"

# Lazy-loaded service references
_calendar_service = None
_gmail_service = None
_tasks_service = None


def _ensure_credentials(force_reauth: bool = False) -> Any:
    """Return an authenticated Google API credentials object.

    Raises ToolError if credentials.json is missing or auth fails.
    """
    oauth_dir = _resolve_oauth_dir()
    credentials_path = oauth_dir / "credentials.json"
    token_path = oauth_dir / "token.pickle"

    if not credentials_path.exists():
        raise ToolError(
            "Google API credentials not found.\n"
            f"Please download your client secrets JSON and save it as:\n"
            f"  {credentials_path}\n\n"
            "Setup steps:\n"
            "1. Visit Google Cloud Console: https://console.cloud.google.com/\n"
            "2. Create a project (or pick an existing one)\n"
            "3. Enable APIs: Google Calendar API, Gmail API, Google Tasks API\n"
            "4. Go to 'APIs & Services' -> 'OAuth consent screen', set User Type to 'External', add your email as a test user\n"
            "5. Go to 'Credentials' -> 'Create Credentials' -> 'OAuth client ID' (Application type: Desktop App)\n"
            "6. Download the JSON file, rename it to 'credentials.json', and place it in:\n"
            f"   {oauth_dir}\n"
            "7. Run: python -m zeno.agent.tools.google"
        )

    import google.auth.exceptions
    from google.auth.transport.requests import Request as AuthRequest
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if not force_reauth and token_path.exists():
        try:
            with open(token_path, "rb") as f:
                creds = pickle.load(f)
        except Exception:
            creds = None

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(AuthRequest())
        except Exception:
            creds = None

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(credentials_path), SCOPES
        )
        creds = flow.run_local_server(port=0, open_browser=True)
        oauth_dir.mkdir(parents=True, exist_ok=True)
        with open(token_path, "wb") as f:
            pickle.dump(creds, f)

    return creds


def _calendar():
    global _calendar_service
    if _calendar_service is None:
        from googleapiclient.discovery import build
        _calendar_service = build("calendar", "v3", credentials=_ensure_credentials())
    return _calendar_service


def _gmail():
    global _gmail_service
    if _gmail_service is None:
        from googleapiclient.discovery import build
        _gmail_service = build("gmail", "v1", credentials=_ensure_credentials())
    return _gmail_service


def _tasks():
    global _tasks_service
    if _tasks_service is None:
        from googleapiclient.discovery import build
        _tasks_service = build("tasks", "v1", credentials=_ensure_credentials())
    return _tasks_service


# ---------------------------------------------------------------------------
# Calendar tools
# ---------------------------------------------------------------------------


@register("getCalendarEvents")
def get_calendar_events(args: Dict[str, Any]) -> Dict[str, Any]:
    """List upcoming Google Calendar events.

    Args:
        max_results: Number of events to return (default 10)
        days_ahead: How many days ahead to look (default 7)
        show_all: Return all details including description/location (default false)
    """
    max_results = min(int(args.get("max_results", 10)), 50)
    days_ahead = max(1, int(args.get("days_ahead", 7)))
    show_all = bool(args.get("show_all", False))

    now = datetime.utcnow()
    time_min = now.isoformat() + "Z"
    time_max = (now + timedelta(days=days_ahead)).isoformat() + "Z"

    try:
        events_result = (
            _calendar()
            .events()
            .list(
                calendarId="primary",
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        items = events_result.get("items", [])
    except Exception as e:
        raise ToolError(f"Failed to fetch calendar events: {e}")

    if not items:
        return {"result": f"No upcoming events found in the next {days_ahead} days.", "events": []}

    result = []
    for ev in items:
        start = ev["start"].get("dateTime", ev["start"].get("date", "Unknown"))
        end = ev["end"].get("dateTime", ev["end"].get("date", "Unknown"))
        entry = {
            "summary": ev.get("summary", "(No title)"),
            "start": start,
            "end": end,
            "htmlLink": ev.get("htmlLink", ""),
        }
        if show_all:
            entry["description"] = ev.get("description", "")
            entry["location"] = ev.get("location", "")
            entry["attendees"] = [
                {"email": a.get("email", ""), "responseStatus": a.get("responseStatus", "unknown")}
                for a in ev.get("attendees", [])
            ]
        result.append(entry)

    return {
        "result": f"Found {len(result)} event(s) in the next {days_ahead} days.",
        "events": result,
    }


@register("createCalendarEvent")
def create_calendar_event(args: Dict[str, Any]) -> Dict[str, Any]:
    """Create a Google Calendar event.

    Args:
        summary: Event title (required)
        description: Event description (optional)
        start_time: Start time in ISO format, e.g. '2026-07-24T14:00:00'
                   If only date like '2026-07-24', creates an all-day event
        end_time: End time in ISO format (required if start_time has time)
        location: Event location (optional)
        attendees: Comma-separated email addresses (optional)
    """
    summary = args.get("summary")
    if not summary:
        raise ToolError("'summary' (event title) is required.")

    start_time = args.get("start_time", "")
    end_time = args.get("end_time", "")
    description = args.get("description", "")
    location = args.get("location", "")

    if not start_time:
        start_time = datetime.utcnow().isoformat()
    if not end_time:
        end_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()

    if "T" not in start_time:
        start_time += "T00:00:00"
        end_time = start_time[:10] + "T23:59:00"

    event = {
        "summary": summary,
        "start": {"dateTime": start_time, "timeZone": "UTC"},
        "end": {"dateTime": end_time, "timeZone": "UTC"},
    }
    if description:
        event["description"] = description
    if location:
        event["location"] = location

    attendees_raw = args.get("attendees", "")
    if attendees_raw:
        event["attendees"] = [{"email": e.strip()} for e in attendees_raw.split(",") if e.strip()]

    try:
        created = _calendar().events().insert(calendarId="primary", body=event).execute()
        return {
            "result": f"Event created: \"{summary}\"",
            "eventLink": created.get("htmlLink", ""),
            "id": created.get("id", ""),
        }
    except Exception as e:
        raise ToolError(f"Failed to create event: {e}")


# ---------------------------------------------------------------------------
# Gmail tools
# ---------------------------------------------------------------------------


@register("sendEmail")
def send_email(args: Dict[str, Any]) -> Dict[str, Any]:
    """Send an email via Gmail.

    Args:
        to: Recipient email address (required)
        subject: Email subject (required)
        body: Email body text (required)
        cc: CC email address (optional)
    """
    to = args.get("to")
    subject = args.get("subject")
    body = args.get("body")
    cc = args.get("cc", "")

    if not to or not subject or not body:
        raise ToolError("'to', 'subject', and 'body' are all required.")

    import base64
    from email.message import EmailMessage

    msg = EmailMessage()
    msg["To"] = to
    msg["Subject"] = subject
    msg["From"] = "me"
    if cc:
        msg["Cc"] = cc
    msg.set_content(body)

    try:
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        _gmail().users().messages().send(userId="me", body={"raw": raw}).execute()
        return {"result": f"Email sent to {to}: \"{subject}\""}
    except Exception as e:
        raise ToolError(f"Failed to send email: {e}")


@register("getEmails")
def get_emails(args: Dict[str, Any]) -> Dict[str, Any]:
    """List recent emails from Gmail inbox.

    Args:
        max_results: Number of emails to return (default 5, max 20)
        query: Gmail search filter (optional), e.g. 'from:someone@email.com' or 'subject:meeting'
    """
    max_results = min(int(args.get("max_results", 5)), 20)
    query = args.get("query", "")

    try:
        result = _gmail().users().messages().list(userId="me", q=query, maxResults=max_results).execute()
        messages = result.get("messages", [])
    except Exception as e:
        raise ToolError(f"Failed to fetch emails: {e}")

    if not messages:
        return {"result": "No emails found matching your criteria.", "emails": []}

    emails = []
    for msg in messages:
        try:
            detail = _gmail().users().messages().get(userId="me", id=msg["id"], format="metadata", metadataHeaders=["From", "Subject", "Date"]).execute()
            headers = {h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])}
            snippet = detail.get("snippet", "")
            emails.append({
                "id": msg["id"],
                "from": headers.get("From", "Unknown"),
                "subject": headers.get("Subject", "(No subject)"),
                "date": headers.get("Date", "Unknown"),
                "snippet": snippet,
            })
        except Exception:
            continue

    return {
        "result": f"Found {len(emails)} email(s).",
        "emails": emails,
    }


# ---------------------------------------------------------------------------
# Google Tasks tools
# ---------------------------------------------------------------------------


@register("getTasks")
def get_tasks(args: Dict[str, Any]) -> Dict[str, Any]:
    """List tasks from Google Tasks.

    Args:
        tasklist: Task list title (default 'My Tasks')
        max_results: Max tasks to return (default 10)
        show_completed: Include completed tasks (default false)
    """
    tasklist_title = args.get("tasklist", "My Tasks")
    max_results = min(int(args.get("max_results", 10)), 50)
    show_completed = bool(args.get("show_completed", False))

    try:
        lists = _tasks().tasklists().list().execute().get("items", [])
        tl = next((t for t in lists if t["title"].lower() == tasklist_title.lower()), None)
        if not tl:
            available = ", ".join(t["title"] for t in lists) if lists else "No task lists found"
            raise ToolError(f"Task list '{tasklist_title}' not found. Available: {available}")
        tl_id = tl["id"]

        tasks_result = _tasks().tasks().list(tasklist=tl_id, maxResults=max_results, showCompleted=show_completed).execute()
        items = tasks_result.get("items", [])
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"Failed to fetch tasks: {e}")

    if not items:
        return {"result": f"No tasks in '{tasklist_title}'.", "tasks": []}

    result = []
    for t in items:
        result.append({
            "title": t.get("title", "(Untitled)"),
            "notes": t.get("notes", ""),
            "due": t.get("due", ""),
            "status": t.get("status", "needsAction"),
            "id": t.get("id", ""),
        })

    return {
        "result": f"Found {len(result)} task(s) in '{tasklist_title}'.",
        "tasks": result,
    }


@register("createTask")
def create_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """Create a task in Google Tasks.

    Args:
        title: Task title (required)
        notes: Task notes/description (optional)
        due: Due date in ISO format, e.g. '2026-07-30' (optional)
        tasklist: Task list title (default 'My Tasks')
    """
    title = args.get("title")
    if not title:
        raise ToolError("'title' is required.")

    notes = args.get("notes", "")
    due = args.get("due", "")
    tasklist_title = args.get("tasklist", "My Tasks")

    body = {"title": title}
    if notes:
        body["notes"] = notes
    if due:
        body["due"] = due

    try:
        lists = _tasks().tasklists().list().execute().get("items", [])
        tl = next((t for t in lists if t["title"].lower() == tasklist_title.lower()), None)
        if not tl:
            available = ", ".join(t["title"] for t in lists) if lists else "No task lists found"
            raise ToolError(f"Task list '{tasklist_title}' not found. Available: {available}")

        created = _tasks().tasks().insert(tasklist=tl["id"], body=body).execute()
        return {
            "result": f"Task created: \"{title}\"",
            "id": created.get("id", ""),
        }
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"Failed to create task: {e}")


def setup_oauth(force_reauth: bool = False) -> None:
    """CLI helper to guide and perform Google OAuth setup."""
    oauth_dir = _resolve_oauth_dir()
    credentials_path = oauth_dir / "credentials.json"
    token_path = oauth_dir / "token.pickle"

    print("=" * 60)
    print("  ZENO Google Suite OAuth Setup (Calendar, Gmail, Tasks)")
    print("=" * 60)
    print(f"\nOAuth Directory: {oauth_dir}")
    print(f"Credentials File: {credentials_path}")
    print(f"Token File:       {token_path}")

    if not credentials_path.exists():
        print("\n[!] credentials.json NOT FOUND!")
        print("\nFollow these steps to obtain credentials.json:")
        print("1. Go to Google Cloud Console: https://console.cloud.google.com/")
        print("2. Create a new project (e.g., 'Zeno Assistant') or select an existing one.")
        print("3. Enable the following 3 APIs under 'APIs & Services' -> 'Library':")
        print("   - Google Calendar API")
        print("   - Gmail API")
        print("   - Google Tasks API")
        print("4. Configure the OAuth Consent Screen ('APIs & Services' -> 'OAuth consent screen'):")
        print("   - User Type: External")
        print("   - App name: ZENO Assistant")
        print("   - Under 'Test users', add your own Google email address.")
        print("5. Create Credentials ('APIs & Services' -> 'Credentials' -> '+ CREATE CREDENTIALS'):")
        print("   - Choose 'OAuth client ID'")
        print("   - Application type: 'Desktop app'")
        print("   - Name: 'ZENO Desktop'")
        print("   - Click 'Create'")
        print("6. Click the Download icon (JSON) next to the created client ID.")
        print("7. Rename the downloaded file to 'credentials.json' and move it to:")
        print(f"   --> {credentials_path}")
        print("\nOnce placed, re-run this setup:")
        print("   python -m zeno.agent.tools.google\n")
        return

    print("\n[✓] credentials.json detected.")
    print("Starting browser OAuth flow for authorization...")
    try:
        creds = _ensure_credentials(force_reauth=force_reauth)
        print("\n[✓] OAuth authorization successful! Token saved to:")
        print(f"    {token_path}")

        print("\nTesting Google APIs connectivity...")
        # 1. Test Calendar
        try:
            cal_res = get_calendar_events({"max_results": 3, "days_ahead": 7})
            print(f"  [✓] Calendar API connected: {cal_res.get('result', '')}")
        except Exception as e:
            print(f"  [!] Calendar API check warning: {e}")

        # 2. Test Gmail
        try:
            mail_res = get_emails({"max_results": 3})
            print(f"  [✓] Gmail API connected: {mail_res.get('result', '')}")
        except Exception as e:
            print(f"  [!] Gmail API check warning: {e}")

        # 3. Test Tasks
        try:
            tasks_res = get_tasks({"max_results": 3})
            print(f"  [✓] Tasks API connected: {tasks_res.get('result', '')}")
        except Exception as e:
            print(f"  [!] Tasks API check warning: {e}")

        print("\n" + "=" * 60)
        print("  ZENO Google Suite integration is fully active!")
        print("=" * 60 + "\n")
    except Exception as e:
        print(f"\n[X] OAuth setup failed: {e}")


__all__ = [
    "get_calendar_events",
    "create_calendar_event",
    "send_email",
    "get_emails",
    "get_tasks",
    "create_task",
    "setup_oauth",
]

if __name__ == "__main__":
    import sys
    force = "--force" in sys.argv
    setup_oauth(force_reauth=force)
