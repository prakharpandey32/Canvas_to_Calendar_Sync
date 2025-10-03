from server import list_courses
cs = list_courses()
print("Courses:", len(cs))
for c in cs[:10]:
    print("-", c.get("id"), c.get("name"))
