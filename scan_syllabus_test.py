from server import list_courses, scan_syllabus_for_dates
cs = list_courses()
first = cs[0]
print("Using:", first["id"], first["name"])
events = scan_syllabus_for_dates(first["id"])
print("Found events:", len(events))
for e in events[:10]:
    print("-", e.get("name"), e.get("start_date"), "||", (e.get("description") or "")[:120])
