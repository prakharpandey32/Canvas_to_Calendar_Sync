from datetime import datetime, timedelta, timezone
from server import get_gcal_service, create_google_event
svc = get_gcal_service()
start = datetime.now(timezone.utc) + timedelta(minutes=10)
evt = create_google_event(svc, {"course_name":"Smoke Test","name":"MCP GCal check",
                                "start_date": start.isoformat()})
print("OK:", bool(evt.get("id")), evt.get("htmlLink",""))
