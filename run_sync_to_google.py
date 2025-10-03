import json

from server import (
    list_courses,
    list_all_assignments,
    get_gcal_service,
    create_google_event,
)


def main() -> None:
    print("Fetching courses...")
    courses = list_courses()
    print("Courses:", len(courses))

    print("Aggregating assignments/events across courses...")
    items = list_all_assignments()
    print("Items:", len(items))

    print("Authorizing Google Calendar service...")
    service = get_gcal_service()

    synced = 0
    errors: list[str] = []
    for it in items:
        try:
            create_google_event(service, it, calendar_id="primary")
            synced += 1
        except Exception as e:
            errors.append(f"{it.get('name')}: {e}")

    print(json.dumps({"synced": synced, "errors": errors[:20]}, indent=2))


if __name__ == "__main__":
    main()


