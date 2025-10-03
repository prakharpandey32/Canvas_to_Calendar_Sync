from datetime import datetime, timedelta, timezone
from server import get_gcal_service
svc = get_gcal_service()
updated_min = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat().replace("+00:00","Z")
resp = svc.events().list(calendarId="primary", singleEvents=True, orderBy="updated",
                         updatedMin=updated_min, maxResults=250).execute()
items = resp.get("items", [])
print("RECENT EVENTS:", len(items))
for e in items[:20]:
    print("-", e.get("summary"), "->", e.get("start",{}).get("dateTime") or e.get("start",{}).get("date"))
