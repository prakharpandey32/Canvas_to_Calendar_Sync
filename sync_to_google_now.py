from server import list_all_assignments, get_gcal_service, create_google_event
svc = get_gcal_service()
synced = 0
for it in list_all_assignments(include_syllabus=True):
    create_google_event(svc, it, calendar_id="primary")
    synced += 1
print("SYNCED:", synced)
