# Google Calendar
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import hashlib

# --- BEGIN FIXED HEADER (put this at the very top) ---
import os
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load .env (only if it exists - for local dev)
ENV_PATH = Path(__file__).with_name(".env")
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH, override=True)

# Canvas config
CANVAS_BASE = (os.getenv("CANVAS_BASE_URL") or "").rstrip("/")
CANVAS_TOKEN = os.getenv("CANVAS_API_TOKEN") or ""

def _canvas_get(path: str, params: dict | None = None):
    """Minimal Canvas GET helper."""
    if not CANVAS_BASE or not CANVAS_TOKEN:
        raise RuntimeError("Canvas not configured. Set CANVAS_BASE_URL and CANVAS_API_TOKEN in .env")
    url = f"{CANVAS_BASE}/api/v1/{path.lstrip('/')}"
    r = requests.get(
        url,
        headers={"Authorization": f"Bearer {CANVAS_TOKEN}"},
        params=params or {},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()

# Plain helpers you want to import in tests
def list_courses():
    return _canvas_get("courses", {"enrollment_state": "active", "per_page": 100})

def list_course_assignments(course_id: int):
    return _canvas_get(f"courses/{course_id}/assignments", {"per_page": 100})
def list_all_assignments(
    include_syllabus: bool = False,
    course_ids: list[int] | None = None
) -> list[dict]:
    """
    Return a flat list of items across courses:
      - Canvas assignments (with due dates)
      - Canvas calendar events (quizzes/exams posted as events)
      - (optional) syllabus-derived exam dates if include_syllabus=True
    Each item will include 'course_id' and 'course_name'.
    """
    courses = [c for c in get_all_courses() if "error" not in c]
    out: list[dict] = []

    for c in courses:
        cid, cname = c["id"], c["name"]
        if course_ids and cid not in course_ids:
            continue

        try:
            assigns = get_course_assignments(cid) or []
        except Exception:
            assigns = []

        try:
            events = get_course_calendar_events(cid) or []
        except Exception:
            events = []

        items = assigns + events

        if include_syllabus:
            try:
                syl = scan_syllabus_for_dates(cid) or []
                items += syl
            except Exception:
                pass

        for it in items:
            it.setdefault("course_id", cid)
            it.setdefault("course_name", cname)
            out.append(it)

    return out
# --- END FIXED HEADER ---
from io import BytesIO
from bs4 import BeautifulSoup
from pdfminer.high_level import extract_text
import dateparser
import re

def _canvas_get_json(path: str, params: dict | None = None):
    return _canvas_get(path, params or {})

def _canvas_get_course(course_id: int):
    # include syllabus_body when available
    try:
        return _canvas_get_json(f"courses/{course_id}", {"include[]": "syllabus_body"})
    except Exception:
        return _canvas_get_json(f"courses/{course_id}")

def _canvas_list_files(course_id: int, per_page: int = 100):
    # Best-effort: bump page size; add real pagination later if needed
    return _canvas_get_json(f"courses/{course_id}/files", {"per_page": per_page})

def _download_canvas_file(file_obj: dict) -> bytes:
    # Canvas file objects usually include a signed 'url' or 'download_url'
    url = file_obj.get("url") or file_obj.get("download_url")
    if not url:
        raise RuntimeError("File has no downloadable URL")
    r = requests.get(url, headers={"Authorization": f"Bearer {CANVAS_TOKEN}"},
                     timeout=60, allow_redirects=True)
    r.raise_for_status()
    return r.content

EXAM_KEYWORDS = re.compile(r"\b(final|midterm|exam|quiz|test)\b", re.I)

# Normalize PDF artifacts (soft hyphen, zero-width, em/en dashes, etc.)
_NORMALIZE_DROP = dict.fromkeys(map(ord, "\u00ad\u200b\u200c\u200d\u2060\uFEFF"), None)
def _normalize_text(s: str) -> str:
    return s.replace("–", "-").replace("—", "-").translate(_NORMALIZE_DROP)

# Helpful regexes
DATE_HINT_RE = re.compile(
    r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}(?:,\s*\d{4})?",
    re.I,
)
TIME_RANGE_RE = re.compile(
    r"(\d{1,2}(?::\d{2})?\s*(?:am|pm))\s*[-–—]\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm))",
    re.I,
)
def _extract_dates_from_text(text: str, course_name: str) -> list[dict]:
    """
    Heuristic:
      â€¢ scan 3-line windows so 'Final Exam' and 'Dec 11, 2â€“5pm' can be on adjacent lines
      â€¢ normalize PDF artifacts
      â€¢ parse date and optional time range
    """
    text = _normalize_text(text)
    lines = text.splitlines()
    out: list[dict] = []

    for i in range(len(lines)):
        window = " ".join(lines[i:i+3])  # current line + next 2 lines
        if not EXAM_KEYWORDS.search(window):
            continue

        # date
        mdate = DATE_HINT_RE.search(window)
        dt = dateparser.parse(mdate.group(0), settings={"PREFER_DATES_FROM": "future"}) if mdate \
             else dateparser.parse(window, settings={"PREFER_DATES_FROM": "future"})
        if not dt:
            continue

        # optional time range
        mtime = TIME_RANGE_RE.search(window)
        if mtime and mdate:
            dt_start = dateparser.parse(f"{mdate.group(0)} {mtime.group(1)}",
                                        settings={"PREFER_DATES_FROM": "future"})
            dt_end   = dateparser.parse(f"{mdate.group(0)} {mtime.group(2)}",
                                        settings={"PREFER_DATES_FROM": "future"})
        else:
            dt_start = dt.replace(hour=9, minute=0, second=0, microsecond=0)
            dt_end   = dt_start.replace(hour=10)

        mkw = EXAM_KEYWORDS.search(window)
        label = mkw.group(1).title() if mkw else "Exam"
        name = f"{label} Exam" if label.lower() in ("midterm", "final") else label

        out.append({
            "type": "event",
            "name": name,
            "course_name": course_name,
            "start_date": dt_start.isoformat(),
            "end_date": dt_end.isoformat(),
            "description": window.strip(),
        })
    return out

"""
Canvas-Outlook Calendar Sync MCP Server

This MCP server connects to Canvas LMS to extract assignment/exam dates
and syncs them to your Outlook calendar.

Prerequisites:
1. Canvas API token from canvas.domain.edu/profile/settings
2. Microsoft Graph API credentials (for Outlook)
3. Install dependencies: pip install mcp requests msal python-dateutil
"""

import asyncio
import os
import json
from datetime import datetime
from typing import List, Dict, Any
import requests
from dateutil import parser as date_parser

from mcp.server import Server
from mcp.types import Tool, Resource, TextContent

# Initialize MCP Server
server = Server("canvas-outlook-sync")

# Configuration (store these in environment variables or config file)
OUTLOOK_CLIENT_ID = os.getenv("OUTLOOK_CLIENT_ID", "")
OUTLOOK_CLIENT_SECRET = os.getenv("OUTLOOK_CLIENT_SECRET", "")
OUTLOOK_TENANT_ID = os.getenv("OUTLOOK_TENANT_ID", "common")

# In-memory storage for session data
session_data = {
    "courses": [],
    "assignments": [],
    "outlook_token": None
}

def scan_syllabus_for_dates(course_id: int) -> list[dict]:
    """
    Returns exam-like events found in:
      1) syllabus HTML (syllabus_body)
      2) relevant PDF(s) in course files (names containing common keywords)
    """
    results: list[dict] = []
    course = _canvas_get_course(course_id)
    cname = course.get("name", f"Course {course_id}")

    # 1) Syllabus HTML
    html = course.get("syllabus_body") or ""
    if html:
        text = BeautifulSoup(html, "html.parser").get_text(separator="\n")
        results.extend(_extract_dates_from_text(text, cname))

    # 2) Candidate PDFs (broader than just â€œsyllabusâ€)
    CANDIDATES = ("syllabus", "schedule", "exam", "midterm", "final", "outline", "calendar")
    try:
        files = _canvas_list_files(course_id)
    except Exception:
        files = []
    pdfs = []
    for f in files:
        if f.get("content-type") != "application/pdf":
            continue
        name = (f.get("display_name","") + " " + f.get("filename","")).lower()
        if any(k in name for k in CANDIDATES):
            pdfs.append(f)
    pdfs = pdfs[:5]  # safety limit

    for f in pdfs:
        try:
            content = _download_canvas_file(f)
            text = extract_text(BytesIO(content)) or ""
            results.extend(_extract_dates_from_text(text, cname))
        except Exception as e:
            # Do not fail the whole scan on one bad PDF
            results.append({
                "type": "error",
                "name": f"PDF parse failed: {f.get('display_name') or f.get('filename')}",
                "description": str(e),
            })

    return results

# ============================================================================
# Canvas API Functions
# ============================================================================

def canvas_request(endpoint: str) -> Dict[str, Any]:
    return _canvas_get(endpoint)


def get_all_courses() -> List[Dict[str, Any]]:
    """Fetch all active courses"""
    try:
        courses = canvas_request("courses?enrollment_state=active")
        return [
            {
                "id": course["id"],
                "name": course["name"],
                "course_code": course.get("course_code", ""),
            }
            for course in courses
            if not course.get("access_restricted_by_date", False)
        ]
    except Exception as e:
        return [{"error": str(e)}]


def get_course_assignments(course_id: int) -> List[Dict[str, Any]]:
    """Fetch assignments for a specific course"""
    try:
        assignments = canvas_request(f"courses/{course_id}/assignments")
        parsed_assignments = []
        
        for assignment in assignments:
            due_date = assignment.get("due_at")
            if due_date:
                parsed_assignments.append({
                    "course_id": course_id,
                    "id": assignment["id"],
                    "name": assignment["name"],
                    "due_date": due_date,
                    "points": assignment.get("points_possible", 0),
                    "type": "assignment"
                })
        
        return parsed_assignments
    except Exception as e:
        return [{"error": str(e)}]


def get_course_calendar_events(course_id: int) -> List[Dict[str, Any]]:
    """Fetch calendar events (including exams) for a course"""
    try:
        events = canvas_request(
            f"calendar_events?context_codes[]=course_{course_id}&type=event"
        )
        parsed_events = []
        
        for event in events:
            start_date = event.get("start_at")
            if start_date:
                parsed_events.append({
                    "course_id": course_id,
                    "id": event["id"],
                    "name": event["title"],
                    "start_date": start_date,
                    "end_date": event.get("end_at", start_date),
                    "description": event.get("description", ""),
                    "type": "event"
                })
        
        return parsed_events
    except Exception as e:
        return [{"error": str(e)}]


# ============================================================================
# Outlook/Microsoft Graph Functions
# ============================================================================

# Delegated auth (Device Code) â€” no client secret needed
def get_outlook_token() -> str:
    """Acquire a delegated Graph token (Calendars.ReadWrite) via Device Code flow."""
    from msal import PublicClientApplication

    app = PublicClientApplication(
        client_id=OUTLOOK_CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{OUTLOOK_TENANT_ID}",
    )
    scopes = ["Calendars.ReadWrite"]

    # Try a silent token first (re-uses cached accounts if youâ€™ve signed in before)
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(scopes=scopes, account=accounts[0])
        if result and "access_token" in result:
            return result["access_token"]

    # Interactive device code (prints a URL + code to the console)
    flow = app.initiate_device_flow(scopes=scopes)
    if "user_code" not in flow:
        raise RuntimeError(f"Device flow init failed: {flow}")
    print(f"\nTo sign in, open {flow['verification_uri']} and enter code: {flow['user_code']}\n")
    result = app.acquire_token_by_device_flow(flow)  # blocks until you complete sign-in
    if "access_token" not in result:
        raise RuntimeError(f"Token error: {result.get('error_description') or result}")
    return result["access_token"]


def create_outlook_event(token: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a calendar event in the signed-in user's calendar (/me/events)."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # Accept either start_date (syllabus/events) or due_date (assignments)
    start_str = event_data.get("start_date") or event_data.get("due_date")
    if not start_str:
        raise ValueError("Missing start_date/due_date in event_data")

    start_dt = date_parser.parse(start_str)
    end_dt = date_parser.parse(event_data.get("end_date", start_str))
    if end_dt == start_dt:
        # Default to a 1-hour window if only a single timestamp is provided
        end_dt = start_dt.replace(hour=start_dt.hour + 1)

    payload = {
        "subject": f"{event_data.get('course_name','Course')}: {event_data.get('name','Item')}",
        "body": {"contentType": "HTML", "content": event_data.get("description", "")},
        "start": {"dateTime": start_dt.isoformat(), "timeZone": "America/New_York"},
        "end":   {"dateTime": end_dt.isoformat(),   "timeZone": "America/New_York"},
        "categories": ["Canvas", event_data.get("type", "item")],
    }

    r = requests.post("https://graph.microsoft.com/v1.0/me/events", headers=headers, json=payload)
    r.raise_for_status()
    return r.json()
# =========================
# Google Calendar Functions
# =========================
GCAL_SCOPES = [(os.getenv("GCAL_SCOPES") or "https://www.googleapis.com/auth/calendar.events")]

def get_gcal_service():
    """
    Returns an authenticated Google Calendar service.
    Uses credentials.json (in this folder) and caches token.json after first consent.
    """
    token_path = Path(__file__).with_name("token.json")
    creds_path = Path(__file__).with_name("credentials.json")

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), GCAL_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not creds_path.exists():
                raise RuntimeError("Missing credentials.json next to server.py (Desktop OAuth client).")
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), GCAL_SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return build("calendar", "v3", credentials=creds, cache_discovery=False)

def _stable_gcal_id(event_data: dict, start_iso: str) -> str:
    """Stable ID to avoid duplicates on re-sync."""
    base = f"{event_data.get('type','item')}|{event_data.get('course_name','')}|{event_data.get('name','')}|{start_iso}"
    return "canvas-" + hashlib.md5(base.encode("utf-8")).hexdigest()

def create_google_event(service, event_data: dict, calendar_id: str = "primary") -> dict:
    """
    Upsert an event to Google Calendar using a stable key in extendedProperties.private.canvas_key.
    Accepts assignment 'due_date' or event 'start_date' (with optional 'end_date').
    """
    start_str = event_data.get("start_date") or event_data.get("due_date")
    if not start_str:
        raise ValueError("Missing start_date/due_date")

    start_dt = date_parser.parse(start_str)
    end_dt = date_parser.parse(event_data.get("end_date", start_str))
    if end_dt == start_dt:
        end_dt = start_dt.replace(hour=(start_dt.hour + 1) % 24)

    start_iso = start_dt.isoformat()
    end_iso = end_dt.isoformat()

    # stable key per Canvas item
    canvas_key = f"{event_data.get('type','item')}:{event_data.get('course_id')}:{event_data.get('id') or event_data.get('name')}"

    body = {
        "summary": f"{event_data.get('course_name','Course')}: {event_data.get('name','Item')}",
        "description": event_data.get("description", ""),
        "start": {"dateTime": start_iso, "timeZone": "America/New_York"},
        "end":   {"dateTime": end_iso,   "timeZone": "America/New_York"},
        "extendedProperties": {"private": {"canvas_key": canvas_key}},
    }

    # Look up by the same key; update if found, otherwise insert
    found = service.events().list(
        calendarId=calendar_id,
        privateExtendedProperty=f"canvas_key={canvas_key}",
        maxResults=1
    ).execute().get("items", [])

    if found:
        ev_id = found[0]["id"]
        return service.events().update(calendarId=calendar_id, eventId=ev_id, body=body).execute()
    else:
        return service.events().insert(calendarId=calendar_id, body=body).execute()

    return service.events().insert(calendarId=calendar_id, body=body).execute()


# ============================================================================
# MCP Server Tools
# ============================================================================

@server.list_tools()
async def list_tools() -> List[Tool]:
    """Define available tools"""
    return [
        Tool(
            name="fetch_courses",
            description="Fetch all active courses from Canvas",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="fetch_course_assignments",
            description="Fetch assignments and due dates for a specific course",
            inputSchema={
                "type": "object",
                "properties": {
                    "course_id": {
                        "type": "integer",
                        "description": "Canvas course ID"
                    }
                },
                "required": ["course_id"]
            }
        ),
        Tool(
            name="fetch_all_assignments",
            description="Fetch assignments from all active courses",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="sync_to_outlook",
            description="Sync fetched assignments/events to Outlook calendar",
            inputSchema={
                "type": "object",
                "properties": {
                    "assignment_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of assignment IDs to sync (or 'all')"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="check_configuration",
            description="Verify API tokens and configuration are set up correctly",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
  Tool(
    name="sync_to_google",
    description="Sync fetched Canvas assignments/events to Google Calendar",
    inputSchema={
        "type": "object",
        "properties": {
            "calendar_id": {
                "type": "string",
                "description": "Target calendar ID; defaults to 'primary'"
            }
        },
        "required": []
    },
),


    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool execution."""
    try:
        if name == "check_configuration":
            status = {
                "canvas_token": "Set" if CANVAS_TOKEN else "Missing",
                "outlook_client_id": "Set" if os.getenv("OUTLOOK_CLIENT_ID") else "Missing",
                "outlook_secret": "Set" if os.getenv("OUTLOOK_CLIENT_SECRET") else "Missing",
            }
            return [TextContent(
                type="text",
                text=f"Configuration Status:\n{json.dumps(status, indent=2)}"
            )]

        elif name == "fetch_courses":
            courses = get_all_courses()
            session_data["courses"] = courses
            return [TextContent(
                type="text",
                text=f"Found {len(courses)} active courses:\n{json.dumps(courses, indent=2)}"
            )]

        elif name == "fetch_course_assignments":
            course_id = int(arguments["course_id"])
            assignments = get_course_assignments(course_id)
            events = get_course_calendar_events(course_id)
            all_items = assignments + events
            session_data["assignments"].extend(all_items)
            return [TextContent(
                type="text",
                text=f"Found {len(all_items)} items for course {course_id}:\n{json.dumps(all_items, indent=2)}"
            )]

        elif name == "fetch_all_assignments":
            if not session_data.get("courses"):
                session_data["courses"] = get_all_courses()

            all_assignments: list[dict] = []
            for course in session_data["courses"]:
                if "error" in course:
                    continue
                cid = course["id"]
                cname = course["name"]

                assignments = get_course_assignments(cid) or []
                events = get_course_calendar_events(cid) or []

                for item in assignments + events:
                    item["course_name"] = cname
                    all_assignments.append(item)

            session_data["assignments"] = all_assignments
            return [TextContent(
                type="text",
                text=f"Found {len(all_assignments)} total assignments/events:\n{json.dumps(all_assignments, indent=2)}"
            )]

        elif name == "sync_to_outlook":
            token = get_outlook_token()
            session_data["outlook_token"] = token

            items = session_data.get("assignments") or []
            if not items:
                return [TextContent(
                    type="text",
                    text="No assignments/events found. Run 'fetch_all_assignments' (and optionally 'scan_syllabus') first."
                )]

            synced_count = 0
            errors: list[str] = []
            for it in items:
                try:
                    create_outlook_event(token, it)
                    synced_count += 1
                except Exception as e:
                    errors.append(f"{it.get('name')}: {e}")

            msg = f"Outlook: synced {synced_count} item(s)"
            if errors:
                msg += "\n\nErrors:\n" + "\n".join(errors[:20])

            return [TextContent(type="text", text=msg)]

        elif name == "sync_to_google":
            service = get_gcal_service()
            calendar_id = (arguments or {}).get("calendar_id", "primary")

            items = session_data.get("assignments") or []
            if not items:
                return [TextContent(
                    type="text",
                    text="No assignments/events found. Run 'fetch_all_assignments' (and optionally 'scan_syllabus') first."
                )]

            synced = 0
            errors: list[str] = []
            for it in items:
                try:
                    create_google_event(service, it, calendar_id=calendar_id)
                    synced += 1
                except Exception as e:
                    errors.append(f"{it.get('name')}: {e}")

            msg = f"Google Calendar: synced {synced} item(s) → {calendar_id}"
            if errors:
                msg += "\n\nErrors:\n" + "\n".join(errors[:20])

            return [TextContent(type="text", text=msg)]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error executing {name}: {e}")]

# ============================================================================
# MCP Server Resources
# ============================================================================

@server.list_resources()
async def list_resources() -> List[Resource]:
    """Define available resources"""
    return [
        Resource(
            uri="canvas://courses",
            name="Canvas Courses",
            description="List of active Canvas courses",
            mimeType="application/json"
        ),
        Resource(
            uri="canvas://assignments",
            name="Canvas Assignments",
            description="All fetched assignments and events",
            mimeType="application/json"
        )
    ]


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Provide resource content"""
    if uri == "canvas://courses":
        return json.dumps(session_data["courses"], indent=2)
    
    elif uri == "canvas://assignments":
        return json.dumps(session_data["assignments"], indent=2)
    
    else:
        raise ValueError(f"Unknown resource: {uri}")


# ============================================================================
# Run Server
# ============================================================================

async def main():
    """Run the server with appropriate transport"""
    # Detect environment
    mode = os.getenv("MCP_TRANSPORT", "stdio").lower()
    
    if mode == "sse":
    # Smithery/Cloud deployment
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Route
    import uvicorn
    
    port = int(os.getenv("PORT", "8000"))
    print(f"Starting SSE server on port {port}...")
    
    sse = SseServerTransport("/messages")
    
    async def handle_sse(request):
        async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
            await server.run(streams[0], streams[1], server.create_initialization_options())
    
    app = Starlette(routes=[Route("/messages", endpoint=handle_sse)])
    uvicorn.run(app, host="0.0.0.0", port=port)
    else:
        # Local Claude Desktop
        from mcp.server.stdio import stdio_server
        
        print("Starting stdio server...")
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )


if __name__ == "__main__":
    # Check configuration
    if not CANVAS_TOKEN:
        print("WARNING: CANVAS_API_TOKEN not set!")
        print("Get your token from: https://canvas.harvard.edu/profile/settings")
    
    asyncio.run(main())


