rows = [{"n": 1}, {"n": 2}]
saved_second = rows[1]
late = [lambda: row["n"] for row in rows]
objects = [lambda row=row: row["n"] for row in rows]
values = [lambda n=row["n"]: n for row in rows]

rows[0]["n"] = 10
rows[1] = {"n": 20}
print("S1", [f() for f in late], [f() for f in objects], [f() for f in values])
saved_second["n"] = 99
print("S2", [f() for f in late], [f() for f in objects], [f() for f in values])
print("rows", rows)

buckets = [[]] * 2
outer_copy = buckets.copy()
buckets[0].append("x")
outer_copy[1].append("y")
print("buckets", buckets)
print("outer-copy", outer_copy)
