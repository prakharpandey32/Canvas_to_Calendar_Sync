from server import list_all_assignments
items = list_all_assignments(include_syllabus=True)
print("WILL SYNC:", len(items))
