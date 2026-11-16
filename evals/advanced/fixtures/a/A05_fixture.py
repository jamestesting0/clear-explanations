from contextlib import contextmanager

events = []

@contextmanager
def transaction():
    events.append("open")
    try:
        yield
    except ValueError:
        events.append("rollback-value")
    else:
        events.append("commit")
    finally:
        events.append("close")

def work(mode):
    try:
        with transaction():
            events.append("body")
            if mode == "parse":
                raise ValueError("bad input")
            if mode == "lookup":
                raise KeyError("missing")
            return "ok"
        events.append("after-with")
        return "recovered"
    finally:
        events.append("outer-finally")
        if mode == "lookup":
            return "forced"

for mode in ("clean", "parse", "lookup"):
    events.clear()
    try:
        result = work(mode)
        print(mode, result, ",".join(events))
    except Exception as exc:
        print(mode, type(exc).__name__, ",".join(events))
