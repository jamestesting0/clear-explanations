import asyncio
from functools import lru_cache

@lru_cache(maxsize=None)
async def raw(key):
    await asyncio.sleep(0)
    return "loaded:" + key

async def coroutine_cache():
    print("first", await raw("x"))
    try:
        print("second", await raw("x"))
    except RuntimeError as exc:
        print("second-error", type(exc).__name__)

async def shared_task(use_shield):
    cache = {}
    gate = asyncio.Event()
    events = []
    async def fetch():
        events.append("fetch:start")
        try:
            await gate.wait()
            return "loaded"
        finally:
            events.append("fetch:finally")
    def get():
        if "x" not in cache:
            cache["x"] = asyncio.create_task(fetch())
        return cache["x"]
    async def reader(name):
        try:
            task = get()
            result = await asyncio.shield(task) if use_shield else await task
            events.append(name + ":" + result)
        except asyncio.CancelledError:
            events.append(name + ":cancelled")
    a = asyncio.create_task(reader("A"))
    b = asyncio.create_task(reader("B"))
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    a.cancel()
    await a
    gate.set()
    await b
    print("shield", use_shield, "cached-cancelled", cache["x"].cancelled())
    print("events", ",".join(events))
    try:
        print("later", await get())
    except asyncio.CancelledError:
        print("later", "cancelled")

asyncio.run(coroutine_cache())
asyncio.run(shared_task(False))
asyncio.run(shared_task(True))
