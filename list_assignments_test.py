from server import list_courses, list_course_assignments
cs = list_courses()
first = cs[0]
print("Using course:", first["id"], first["name"])
items = list_course_assignments(first["id"])
print("Assignments:", len(items))
for a in items[:10]:
    print("-", a.get("name"), a.get("due_at"))
