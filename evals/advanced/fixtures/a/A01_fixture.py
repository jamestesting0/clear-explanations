import asyncio

async def scenario(cancel_a):
    state = {"available": 100, "committed": 0}
    trace = []
    gate = asyncio.Event()

    async def reserve(name, amount):
        state["available"] -= amount
        trace.append(f"{name}:reserved")
        try:
            if name == "A":
                await gate.wait()
            else:
                await asyncio.sleep(0)
                raise ValueError("B declined")
            state["committed"] += amount
            trace.append(f"{name}:committed")
            return amount
        except BaseException:
            state["available"] += amount
            trace.append(f"{name}:released")
            raise
        finally:
            trace.append(f"{name}:cleanup")

    a = asyncio.create_task(reserve("A", 30))
    b = asyncio.create_task(reserve("B", 20))
    try:
        await asyncio.gather(a, b)
    except ValueError:
        trace.append("caller:caught")
    print("after-gather", state, a.done(), a.cancelled())
    if cancel_a:
        a.cancel()
        try:
            await a
        except asyncio.CancelledError:
            trace.append("caller:cancel-observed")
    else:
        gate.set()
        await a
    print("final", state)
    print("trace", ",".join(trace))

asyncio.run(scenario(False))
asyncio.run(scenario(True))
