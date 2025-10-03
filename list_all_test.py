from server import list_all_assignments
items = list_all_assignments(include_syllabus=True)
print(len(items), "items")
for it in items[:5]:
    print("-", it.get("course_name"), "|", it.get("name"), "|", it.get("due_date") or it.get("start_date"))
