"""Original synthetic benchmark authoring and deterministic gold verification.

This file never calls a model or reads any skill or prior benchmark response.
"""
import collections
import decimal
import fractions
import hashlib
import json
import math
import pathlib
import platform
import re
import sqlite3
import statistics
import subprocess
import sys
import textwrap

ROOT = pathlib.Path(__file__).resolve().parent
CASES = []
RUBRICS = {}
VERIFICATIONS = {}
SOURCES = {}

def clean(s):
    return textwrap.dedent(s).strip()

def fence(code, language):
    return f"```{language}\n{clean(code)}\n```"

def add(case_id, category, prompt, must_include, must_not, critical_errors,
        *, constraints=None, source_ids=None, complexity_features=None,
        source_expectations=None, verification=None):
    CASES.append({
        "id": case_id,
        "split": "development" if int(case_id[1:]) <= 24 else "validation",
        "category": category,
        "prompt": clean(prompt),
        "constraints": constraints or {},
        "source_ids": source_ids or [],
        "complexity_features": complexity_features or [],
    })
    RUBRICS[case_id] = {
        "must_include": must_include,
        "must_not": must_not,
        "critical_errors": critical_errors,
        "source_expectations": source_expectations or [],
        "verification": verification or [],
    }

def execute(case_id, language, code, expected=None):
    suffix = {"python": ".py", "javascript": ".js", "java": ".java"}[language]
    path = ROOT / (case_id + "_fixture" + suffix)
    path.write_text(clean(code) + "\n")
    command = {"python": [sys.executable, str(path)],
               "javascript": ["node", str(path)],
               "java": ["java", str(path)]}[language]
    result = subprocess.run(command, text=True, capture_output=True, timeout=15)
    if result.returncode:
        raise RuntimeError(f"{case_id}: {result.stderr}")
    output = result.stdout.strip()
    if expected is not None:
        assert output == expected, (case_id, output, expected)
    VERIFICATIONS[case_id] = {
        "method": "executed_fixture",
        "command": command,
        "fixture_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "exit_code": result.returncode,
        "stdout": output,
        "stderr": result.stderr.strip(),
        "checks": [],
    }
    return output

def check(case_id, label, actual, expected, tolerance=None):
    passed = (math.isclose(actual, expected, rel_tol=tolerance, abs_tol=tolerance)
              if tolerance is not None else actual == expected)
    assert passed, (case_id, label, actual, expected)
    record = VERIFICATIONS.setdefault(case_id, {"method": "executed_calculation_or_simulation", "checks": []})
    record["checks"].append({"label": label, "actual": actual, "expected": expected,
                             "tolerance": tolerance, "passed": passed})

def sql_check(case_id, schema, query):
    db = sqlite3.connect(":memory:")
    db.executescript(clean(schema))
    rows = db.execute(clean(query)).fetchall()
    db.close()
    VERIFICATIONS.setdefault(case_id, {"method": "executed_sqlite_query", "sqlite_version": sqlite3.sqlite_version,
                                       "checks": []})
    return [list(r) for r in rows]

def write_outputs():
    for case in CASES:
        count = len(case["prompt"].split())
        assert 400 <= count <= 1000, (case["id"], count)
        assert isinstance(case["constraints"], dict)
        assert len(RUBRICS[case["id"]]["must_include"]) >= 6
    (ROOT / "cases.json").write_text(json.dumps(CASES, ensure_ascii=False, indent=2) + "\n")
    (ROOT / "rubric.json").write_text(json.dumps(RUBRICS, ensure_ascii=False, indent=2) + "\n")
    (ROOT / "verification.json").write_text(json.dumps({
        "fixture_origin":"original synthetic material",
        "python_version":platform.python_version(),
        "sqlite_version":sqlite3.sqlite_version,
        "node_version":subprocess.run(["node","--version"], text=True, capture_output=True).stdout.strip(),
        "java_version":subprocess.run(["java","--version"], text=True, capture_output=True).stdout.strip(),
        "case_count":len(CASES),
        "word_counts":{c["id"]:len(c["prompt"].split()) for c in CASES},
        "cases":VERIFICATIONS,
        "primary_sources":SOURCES,
    }, ensure_ascii=False, indent=2) + "\n")


# A01: cancellation, failure, and state are independently observable.
a01_code = r'''
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
'''
a01_out = execute("A01", "python", a01_code)
check("A01", "both intermediate states keep A reserved", a01_out.count("after-gather {'available': 70, 'committed': 0} False False"), 2)
check("A01", "first terminal allocation", "final {'available': 70, 'committed': 30}" in a01_out, True)
check("A01", "explicit cancellation terminal allocation", "final {'available': 100, 'committed': 0}" in a01_out, True)
add("A01", "python_async_failure_and_cancellation", f'''
This is an original synthetic incident packet; no production customer or system is represented. I am trying to understand a reservation bug before changing our concurrency code. The example runs on Python 3.12 with the default event loop, and no other tasks, signals, threads, or callbacks mutate the dictionary. Treat each scenario as a fresh process-level experiment with independent state. The printed dictionaries are copied to the terminal immediately, not retained as references by a logger.

[A01-CODE] The reduced program is:

{fence(a01_code, "python")}

[A01-NOTES] A reviewer wrote: “A failed gather cancels everything it was waiting for. Therefore the exception handler is the rollback boundary, and the state after it must always have available equal to 100.” Another reviewer says the example only appears to work because cancelling a task skips its exception handlers and finally blocks. Both are arguing from short examples that ended immediately after the exception was caught. Our real request handler remains alive to record a response and another task can continue working while that happens.

The business requirement is specific: a failed group operation must not return a success response for any participant, must release every uncommitted reservation before the failure response is sent, and must not reverse an already committed external transfer. In this reduced program, committing only changes an in-memory counter; that simplification should not be silently carried over to a payment processor. The available and committed fields describe quantities, not booleans, and the invariant starts as their sum being 100 except while uncommitted reservations are outstanding.

Please explain what the program actually prints at the two after-gather checkpoints and the two final checkpoints, and give the meaningful event order for each run. Reconcile those observations with both reviewers' claims. I also need to know which part of the behavior comes from gather, which part comes from awaiting the explicitly cancelled task, and why replacing BaseException with Exception would matter to this particular cleanup strategy. Finally, suggest a concrete structure for satisfying the stated group requirement and identify the extra design work that an external commit would require. Explain any boundary where the toy example stops proving the production claim; do not assume that changing one asyncio API makes external side effects transactional.
''', [
    "Both after-gather checkpoints have available 70 and committed 0; A is neither done nor cancelled.",
    "When A is released through the gate, final state is available 70 and committed 30.",
    "When A is explicitly cancelled and awaited, final state is available 100 and committed 0, with cancellation observed by the caller.",
    "The core order is A reserved, B reserved, B released, B cleanup, caller caught; the successful tail is A committed then A cleanup, and the cancelled tail is A released then A cleanup then caller cancellation observed.",
    "Default gather propagates B's exception without cancelling A; ending the whole asyncio.run scope would introduce a separate shutdown-cancellation effect.",
    "CancelledError is caught by BaseException here and would not be caught by Exception in Python 3.12; finally would still execute, but this particular refund would not.",
    "A proposed group-failure structure cancels or otherwise stops remaining work and awaits completion of cleanup before returning; TaskGroup with suitable per-task cleanup or an explicit cancel-and-await pattern is acceptable.",
    "An external commit needs a distinct idempotency, compensation, or commit protocol; task cancellation cannot undo a completed external effect."
], ["Do not claim finally is skipped on cancellation.", "Do not treat the in-memory balance example as proof of atomic external payments."],
["Claims gather automatically cancelled A at the checkpoint.", "Claims the cancellation run commits 30 or fails to release A despite the shown BaseException handler."],
source_ids=["A01-CODE", "A01-NOTES"], complexity_features=["two controlled executions", "exception versus cancellation", "intermediate-state invariant", "production boundary"],
source_expectations=["Tie execution claims to A01-CODE and distinguish the reviewers' assertions in A01-NOTES from authoritative behavior."], verification=["Python 3.12 fixture executed; exact stdout stored in verification.json."])


a02_code = r'''
const trace = [];
const log = value => trace.push(value);
log("start");
Promise.resolve()
  .then(() => {
    log("first");
    queueMicrotask(() => log("nested"));
    return Promise.resolve("row");
  })
  .then(value => {
    log("write:" + value);
    throw new Error("write-failed");
  })
  .catch(error => {
    log("caught:" + error.message);
    return "fallback";
  })
  .finally(() => {
    log("audit");
    throw new Error("audit-failed");
  })
  .then(value => log("success:" + value),
        error => log("outer:" + error.message));
queueMicrotask(() => log("peer"));
(async () => { await 0; log("await-resumed"); })();
setTimeout(() => {
  log("timer");
  console.log(trace.join(" | "));
}, 0);
log("end");
'''
a02_out = execute("A02", "javascript", a02_code)
check("A02", "full event order", a02_out,
      "start | end | first | peer | await-resumed | nested | write:row | caught:write-failed | audit | outer:audit-failed | timer")
add("A02", "javascript_promise_order_and_error_replacement", f'''
This is an original synthetic debugging exercise. We reduced a browser-side save bug to the program below and ran the same program as a standalone modern Node script. Assume the standard JavaScript promise job queue, queueMicrotask, and setTimeout behavior; there are no process.nextTick calls, fake timers, host event handlers, or other application tasks. The array is the actual event recorder, so terminal buffering does not explain an unexpected order.

[A02-CODE]

{fence(a02_code, "javascript")}

[A02-REVIEW] The proposed incident summary says: “The nested microtask must run immediately when it is scheduled because it is inside an already running microtask. The async function cannot resume until the timer because await always means waiting for I/O. Our catch converts a write error into a fallback value, and finally only performs housekeeping, so the success handler eventually receives fallback.” Each sentence has been used to justify a different patch, and I suspect we are merging several independent misunderstandings.

[A02-REQUIREMENT] The real save operation is allowed to return a fallback draft if its database write fails. Audit logging is desirable, but its failure must not replace either a successful save result or the original save failure. If a write fails and no fallback is available, that write failure must reach the caller. Audit failures must still be observed and sent to a separate error collector. The collector's own delivery can be asynchronous, but any failure in that delivery needs an explicit policy rather than becoming an unhandled rejected promise. Nothing in this packet grants a guarantee that an audit call finishes before the page closes.

Please reconstruct the event sequence, including which success or error handler runs at the end. Explain the difference between placing a callback in a queue and running it, and account for the relative positions of peer, await-resumed, and nested rather than just saying “microtasks first.” Also explain why returning the already resolved promise from the first callback still does not make the next callback run synchronously. We do not need a count of undocumented internal promise jobs; we need a correct observable order and a useful explanation.

Then evaluate the incident summary and propose a small correction to the audit path that meets the actual requirement. Be explicit about whether your correction waits for audit, lets it continue independently, or makes that a documented choice. Show how its error handling preserves the operation's outcome, including the no-fallback path. Avoid fixing the example merely by deleting the audit call or suppressing every error, because the requirement includes recording audit failures. If different host environments could change some unrelated scheduling details, keep that caveat separate from the order forced by this self-contained program.
''', [
    "Give the observable order start, end, first, peer, await-resumed, nested, write:row, caught:write-failed, audit, outer:audit-failed, timer.",
    "Explain that queueMicrotask enqueues nested after the already queued peer and await continuation; it does not reenter immediately.",
    "Explain that awaiting 0 yields and resumes as a promise-related job without requiring external I/O or the timer.",
    "Returning a fulfilled promise is adopted by the chain and later reactions remain asynchronous.",
    "The catch fulfills its resulting promise with fallback, but the throwing finally rejects the subsequent promise with audit-failed.",
    "The success handler is not called and the final rejection handler observes the audit error rather than the write error.",
    "A valid audit correction catches audit failure on the audit operation's own branch, records it according to an explicit collector-failure policy, and preserves the prior value or rejection.",
    "State whether the corrected flow awaits audit or detaches it, and acknowledge that detached work has no completion guarantee before shutdown."
], ["Do not say finally can never change a chain's outcome.", "Do not rely on process.nextTick behavior absent from the supplied code."],
["Places timer or nested before peer and await-resumed.", "Says the success callback receives fallback in the shown program.", "Proposes unobserved rejected audit or collector promises as a fully compliant fix."],
source_ids=["A02-CODE", "A02-REVIEW", "A02-REQUIREMENT"], complexity_features=["nested job scheduling", "error replacement", "competing requirements", "correction preserving success and failure"],
source_expectations=["Use the code as scheduling evidence and the requirement as the standard for evaluating a patch."], verification=["Standalone Node fixture executed and exact event sequence asserted."])


a03_code = r'''
import java.util.*;

class A03_fixture {
    public static void main(String[] args) {
        var base = new ArrayList<StringBuilder>();
        for (String s : List.of("A", "B", "C", "D"))
            base.add(new StringBuilder(s));
        var window = base.subList(1, 3);
        var copied = List.copyOf(window);
        var wrapped = Collections.unmodifiableList(window);
        window.set(0, new StringBuilder("B2"));
        base.get(2).append("!");
        System.out.println("base=" + base);
        System.out.println("copied=" + copied);
        System.out.println("wrapped=" + wrapped);
        try { copied.add(new StringBuilder("X")); }
        catch (UnsupportedOperationException e) {
            System.out.println("copied-add=blocked");
        }
        base.add(new StringBuilder("E"));
        try { System.out.println("window-size=" + window.size()); }
        catch (ConcurrentModificationException e) {
            System.out.println("window-size=invalidated");
        }
        System.out.println("copied-after=" + copied);
    }
}
'''
a03_out = execute("A03", "java", a03_code)
check("A03", "observed supplied JDK trace", a03_out, "base=[A, B2, C!, D]\ncopied=[B, C!]\nwrapped=[B2, C!]\ncopied-add=blocked\nwindow-size=invalidated\ncopied-after=[B, C!]")
add("A03", "java_collection_views_and_mutable_elements", f'''
This is an original synthetic Java review packet. A reporting library hands a caller a list of mutable labels. The developer intended to provide a frozen snapshot, but another team says the objects still change after publication. We have reduced the issue to one thread, so please do not attribute any of the displayed behavior to a race. The supplied trace was observed on OpenJDK 21; distinguish that implementation observation from any broader API guarantee.

[A03-CODE]

{fence(a03_code, "java")}

[A03-INTENT] The library's public contract currently says: “The returned report is read-only. It contains the labels that existed at the instant the report was requested. Later edits to the source list and later edits to individual labels cannot change the report.” All three sentences matter: callers want to keep a report for an audit comparison next week. The original team believed either List.copyOf or Collections.unmodifiableList would satisfy the entire contract. Someone else proposed calling List.copyOf twice, assuming that a second copy also copies every StringBuilder.

[A03-OBSERVATION] In the local run, base displayed A, B2, C!, D; copied displayed B, C!; wrapped displayed B2, C!; adding to copied was blocked; asking for window's size after base.add raised ConcurrentModificationException; and copied still displayed B, C! afterward. A bug report currently describes the last exception as proof that Java silently started a second thread, because the word concurrent appears in its name. The report also says copied is immutable because add failed, even though its C label changed.

[A03-API] Primary API source, paraphrased from the Java 21 List specification: copyOf prevents structural edits through the result but does not freeze mutable elements. A subList's semantics are undefined after its backing list is structurally changed outside that view. Source: https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/List.html

Explain how the references and list structures differ across base, window, copied, and wrapped at each mutation. In particular, why does replacing the B element affect some lists but appending an exclamation mark to C affects others? Why can an unmodifiable list still fail the requested snapshot contract? Account for both the successful and failing operations without treating exception names as complete explanations.

Please propose a return type and construction approach that actually meet the contract for this example. We can change the exported element type, and strings are acceptable to callers, but we cannot prevent the library from continuing to modify its internal builders. Also explain the documented boundary after a structural modification to a backing list outside a subList: the observed exception is useful evidence, but our replacement design must not depend on that exact exception occurring on every implementation or every later access. A good answer should tell the maintainer which claim about immutability is safe to put in the contract and which claim would need a deeper copy policy for more complex element types.
''', [
    "Distinguish base storage, the backed subList view, the unmodifiable wrapper over that view, and the separate unmodifiable list structure returned by copyOf.",
    "Explain window.set replacing B with a new builder: base/window/wrapped see B2, whereas copied keeps the original B reference.",
    "Explain the shared C builder being mutated, so both copied and wrapped display C!.",
    "Explain that preventing add/set through a collection API does not freeze mutable objects reachable through it.",
    "Explain the local ConcurrentModificationException without inventing another thread; structural modification outside the view invalidates the conditions for using the backed view.",
    "Avoid treating the exact observed post-modification exception as a portable guarantee: subList semantics become undefined after the specified external structural modification.",
    "A correct snapshot can map builders to String values at capture time and return an unmodifiable independent list of those immutable values.",
    "A second copyOf is still shallow with respect to mutable elements and does not implement a deep snapshot."
], ["Do not equate unmodifiable containers with deeply immutable object graphs.", "Do not promise a particular fail-fast exception for all later subList operations."],
["Claims copied must display B2.", "Claims copyOf clones the StringBuilder objects.", "Claims the exception proves concurrent threads existed."],
source_ids=["A03-CODE", "A03-INTENT", "A03-OBSERVATION", "A03-API"], complexity_features=["three aliasing relationships", "mutable element versus structural mutation", "observed versus specified behavior", "API contract repair"],
source_expectations=["Use A03-OBSERVATION only for the stated OpenJDK run; API portability claim is additionally grounded in the preserved Java List documentation source."], verification=["Java source-file execution succeeded on OpenJDK 21; full output asserted.", "Primary Java API documentation required for the subList portability caveat."])


a04_schema = r'''
CREATE TABLE customer (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, status TEXT);
CREATE TABLE line (order_id INTEGER, quantity INTEGER, unit_price INTEGER);
CREATE TABLE refund (order_id INTEGER, amount INTEGER);
INSERT INTO customer VALUES (1,'Ada'),(2,'Ben'),(3,'Cy');
INSERT INTO orders VALUES (10,1,'paid'),(11,1,'cancelled'),(20,2,'paid');
INSERT INTO line VALUES (10,2,50),(10,1,60),(11,1,999),(20,1,40);
INSERT INTO refund VALUES (10,15),(10,5);
'''
a04_bad = r'''
SELECT c.name, COUNT(o.id) AS paid_orders,
       SUM(l.quantity * l.unit_price) AS gross,
       SUM(r.amount) AS refunds,
       SUM(l.quantity * l.unit_price) - COALESCE(SUM(r.amount),0) AS net
FROM customer c
LEFT JOIN orders o ON o.customer_id = c.id
LEFT JOIN line l ON l.order_id = o.id
LEFT JOIN refund r ON r.order_id = o.id
WHERE o.status = 'paid'
GROUP BY c.id, c.name
ORDER BY c.id;
'''
a04_fix = r'''
WITH lg AS (SELECT order_id, SUM(quantity*unit_price) AS gross FROM line GROUP BY order_id),
rg AS (SELECT order_id, SUM(amount) AS refunds FROM refund GROUP BY order_id)
SELECT c.name, COUNT(o.id), COALESCE(SUM(lg.gross),0), COALESCE(SUM(rg.refunds),0),
       COALESCE(SUM(lg.gross),0)-COALESCE(SUM(rg.refunds),0)
FROM customer c
LEFT JOIN orders o ON o.customer_id=c.id AND o.status='paid'
LEFT JOIN lg ON lg.order_id=o.id
LEFT JOIN rg ON rg.order_id=o.id
GROUP BY c.id,c.name ORDER BY c.id;
'''
check("A04", "faulty query rows", sql_check("A04", a04_schema, a04_bad), [["Ada",4,320,40,280],["Ben",1,40,None,40]])
check("A04", "fixed query rows", sql_check("A04", a04_schema, a04_fix), [["Ada",1,160,20,140],["Ben",1,40,0,40],["Cy",0,0,0,0]])
add("A04", "sql_outer_join_fanout_and_aggregation_grain", f'''
This is an original synthetic database exercise using SQLite-compatible SQL and integer cents. We are investigating a revenue dashboard that looks plausible when tested on one customer but overstates revenue in the full dataset. The tables below contain the entire example; there are no hidden rows, triggers, duplicate primary keys, or currency conversions. Each line and each refund is an independent child record of an order.

[A04-DATA]

{fence(a04_schema, "sql")}

[A04-QUERY] The dashboard currently executes:

{fence(a04_bad, "sql")}

[A04-CONTRACT] The requested output has one row for every customer, even a customer who has never placed an order. Paid orders alone contribute to the metrics. paid_orders means the number of paid orders, gross is the sum of their line amounts, refunds is the sum of their refund records, and net is gross minus refunds. Empty monetary totals should display zero. A paid order is allowed to have no lines or no refunds; the counts and zero handling must still make sense. The display layer must not repair or reinterpret the SQL result.

[A04-REVIEW] A developer proposes moving the paid predicate into the first ON clause and changing COUNT(o.id) to COUNT(DISTINCT o.id). They believe those two edits fix everything because every customer then survives the LEFT JOIN. A second developer proposes adding DISTINCT inside each SUM, saying duplicated rows will disappear and equal amounts are interchangeable anyway. We have previously had two genuinely different line items with identical prices, so an explanation must say whether that matters to the proposed fix.

Please show what the current query returns and explain how those numbers arise from the intermediate joined rows. Then give the correct business result for this dataset and a query or precise query structure that produces it under the stated contract. Identify the grain of each intermediate relation: customer, order, line, refund, or something else. I need to understand why a change can repair the customer population while leaving the money wrong, and why a count can become correct while two sums remain wrong.

Also discuss the difference between an absent refund, a zero refund amount, and an empty customer aggregate here. Explain what COALESCE can and cannot repair. The goal is to approve a robust query structure, so please address both review proposals and the no-lines edge case; do not just print the three desired rows or special-case Ada's order. If a rewrite uses pre-aggregation, explain which keys make the later joins safe from this particular multiplication and where a future extra one-to-many join could reintroduce the same bug.
''', [
    "The faulty output is Ada count 4, gross 320, refunds 40, net 280; Ben count 1, gross 40, refunds NULL, net 40; Cy is absent.",
    "Ada order 10 expands to four combinations of two lines and two refunds, repeating each child measure twice.",
    "The WHERE condition filters away null-extended customer rows, while moving it into the order join preserves customers.",
    "The correct output is Ada 1/160/20/140, Ben 1/40/0/40, Cy 0/0/0/0 in count/gross/refund/net order.",
    "COUNT(DISTINCT order id) repairs the count for this fanout but leaves the two sums multiplied.",
    "SUM(DISTINCT amount) is not a general repair because separate legitimate equal-valued records would collapse.",
    "A correct rewrite aggregates each child independently to one row per order before joining or uses equivalent correlated aggregates, and includes paid order selection in a customer-preserving structure.",
    "COALESCE handles absent aggregates but cannot correct duplicated contributions; count the order identifier so a paid order with no lines still counts."
], ["Do not mix dollar formatting into integer-cent arithmetic.", "Do not treat DISTINCT monetary values as record identity."],
["Endorses only moving WHERE plus COUNT DISTINCT as a complete revenue fix.", "Endorses SUM DISTINCT as generally correct.", "Drops Cy from the required result."],
source_ids=["A04-DATA", "A04-QUERY", "A04-CONTRACT", "A04-REVIEW"], complexity_features=["two independent one-to-many joins", "null extension", "business-grain reasoning", "plausible partial fixes"],
source_expectations=["Ground numeric results in A04-DATA and population/empty-value choices in A04-CONTRACT."], verification=["Both faulty and corrected queries executed against fresh in-memory SQLite databases."])


a05_code = r'''
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
'''
a05_out = execute("A05", "python", a05_code)
check("A05", "complete control-flow trace", a05_out,
      "clean ok open,body,commit,close,outer-finally\nparse recovered open,body,rollback-value,close,after-with,outer-finally\nlookup forced open,body,close,outer-finally")
add("A05", "python_context_manager_suppression_and_finally_return", f'''
This is an original synthetic Python service example. A request processor has two different cleanup mechanisms, and the team has confused “the cleanup ran” with “the failure reached the caller.” The names transaction, commit, and rollback below are event labels only: this example has no actual database, no implicit framework retry, and no magic transactional decorator beyond contextlib.contextmanager. We want to reason about Python control flow before reconnecting it to real persistence.

[A05-CODE]

{fence(a05_code, "python")}

[A05-CLAIMS] The author believes that catching ValueError inside the generator is equivalent to logging it and allowing the with statement to raise it again automatically. They also believe the finally return is harmless because the exception has already been selected for propagation by the time the finalizer runs. A reviewer states that removing the final return would make all three modes raise, because any return from inside a with block bypasses the generator's normal path. These explanations cannot all be right, but the production logs contain close in every case, which has obscured the disagreement.

[A05-REQUIREMENT] A clean request should return ok and perform the successful completion action. A parse failure should perform rollback, close the resource, and remain visible as the original ValueError to the caller. A missing lookup should perform rollback, close the resource, and remain visible as the original KeyError. We do not want to convert errors into recovered or forced responses, and we do not want a cleanup error to be silently hidden if a cleanup operation itself later becomes fallible. The original exception type matters to the caller's retry policy.

Explain the value or exception that the caller observes for each mode and the event ordering that leads there. Please locate exactly where each original exception is suppressed in the shown program. Distinguish the context manager's exit behavior from the outer function's finally behavior, and explain why seeing close in a log proves less than the author thinks. Also explain which paths reach after-with and why the successful return still permits the generator's else clause to run.

Then propose a small refactor that meets the requirement for these ordinary exceptions. It is acceptable to show corrected pseudocode if you define the exception-handling behavior precisely. Explain the use of re-raising the active exception, why returning from finally is dangerous here, and how a more complete design should represent both an operation failure and a cleanup failure if they happen together. Do not introduce broad suppression as the solution, and do not infer from these three ordinary exception types that cancellation or interpreter shutdown has also been handled. We are looking for a correct model of unwinding, not merely advice to avoid the finally keyword.
''', [
    "Clean returns ok with events open, body, commit, close, outer-finally.",
    "Parse returns recovered with rollback-value and close before after-with and outer-finally; the context manager suppresses its ValueError because it catches it and does not re-raise.",
    "Lookup returns forced with open, body, close, outer-finally; no rollback or after-with occurs in the shown code.",
    "The lookup KeyError initially leaves the context manager but is suppressed by the return in outer finally.",
    "A normal return inside with still runs context-manager exit and the generator's successful else path before the function returns.",
    "A correction rolls back the intended ordinary failures, uses a bare re-raise to preserve them, commits only on normal completion, always closes, and removes the return from finally.",
    "Seeing close establishes that cleanup was entered, not that rollback happened or that the original exception propagated.",
    "Discuss a deliberate policy for simultaneous body and cleanup failures, such as chaining or grouping, without falsely promising that a simple finally preserves the original as the primary exception under all failures."
], ["Do not claim a return from within with bypasses exit.", "Do not silently broaden the guarantee to cancellation or shutdown."],
["Claims parse raises ValueError in the shown program.", "Claims lookup raises KeyError in the shown program.", "Retains a finally return while claiming original errors reliably propagate."],
source_ids=["A05-CODE", "A05-CLAIMS", "A05-REQUIREMENT"], complexity_features=["generator context manager", "two suppression sites", "return during unwinding", "dual-failure design"],
source_expectations=["Attribute observed behavior to A05-CODE and proposed error semantics to A05-REQUIREMENT."], verification=["All three paths executed and exact traces asserted."])


a06_provider = {}
for key in ["attempt-1", "attempt-2"]:
    a06_provider.setdefault(key, 700)
check("A06", "retry-scoped keys total charged", sum(a06_provider.values()), 1400)
a06_stable = {}
for key in ["merchant-M/order-91", "merchant-M/order-91"]:
    a06_stable.setdefault(key, 700)
check("A06", "stable key total charged within retention", sum(a06_stable.values()), 700)
add("A06", "distributed_idempotency_and_crash_boundaries", '''
This is an original synthetic incident packet. All provider rules below are invented for this exercise and must be treated as the complete service contract; do not substitute the rules of a real payment vendor. Please answer in Spanish. Our team needs to understand why a queue consumer charged twice even though the database contains only one completed order, and whether our proposed repair establishes the guarantee the product team actually requested.

[A06-PROVIDER] POST /charge takes merchant, amount_cents, reference, and idempotency_key. For a given merchant and key, the provider atomically stores the first successful request and its response for exactly 24 hours. Repeating the same payload with that key during retention returns that response without another charge. Reusing the key with a different amount returns a conflict. After expiration the same key may create a new charge. reference is searchable but is not unique. Search results may lag accepted charges by five seconds. The provider does not participate in our database transaction and has no rollback endpoint.

[A06-CONSUMER] A worker receives order 91 for 700 cents. It begins a local database transaction, checks whether order 91 is completed, and, if not, calls /charge. The key is a new random attempt identifier generated for each delivery. After a successful provider response it writes the provider transaction identifier into orders, sets status=completed, commits, and acknowledges the queue message. The orders table has a unique order_id. The queue redelivers messages whose acknowledgements it did not record. Two workers can receive the same order concurrently, but local uniqueness prevents two committed orders rows with order_id=91.

[A06-TRACE] At 10:00:00 the provider accepts attempt-1 and creates charge C501 for 700 cents. At 10:00:01 the worker process dies before its local transaction commits. At 10:00:04 a second delivery sees no completed row. The second worker generates attempt-2; the provider creates C502 for another 700 cents. At 10:00:05 the worker commits one completed orders row naming C502 and the queue records its acknowledgement. The provider ledger later contains both C501 and C502. None of these timestamps is within five seconds of the key's expiration.

[A06-PROPOSALS] One proposal is to strengthen the unique order constraint and keep everything else unchanged. Another is to mark the order completed before calling the provider. A third is to retry with a stable merchant-and-order key and store an explicit pending state before the network call. The product requirement is that a valid order eventually has one charge and one completed local record, even when a worker crashes at any instruction. Queue redelivery may occur more than 24 hours later, and humans may also initiate recovery.

Explain the two charges and the single row without calling either database corrupted. Compare the failure windows in all three proposals. Describe which parts the stable-key design can actually guarantee under this provider contract, what a pending state means when a network result is unknown, and why an empty immediate search result is not proof that no charge exists. Give a concrete recovery approach for the ordinary within-retention case and identify what additional provider capability or operational restriction would be needed for the unrestricted product requirement. Distinguish deduplicating message delivery, deduplicating an external side effect, and reconciling local knowledge about that side effect.
''', [
    "Explain that C501 persists despite local rollback and that retry-scoped attempt-2 creates C502; total charged is 1400 cents while one row records only C502.",
    "The local unique order constraint does not atomically cover provider charges and cannot by itself prevent the duplicate external side effect.",
    "Marking completed before the call introduces a crash window with a completed local record but no charge.",
    "Use a durable stable key scoped to merchant and order plus consistent payload for retries within the 24-hour retention period.",
    "Treat pending/unknown as incomplete knowledge, retain recovery metadata, retry or query using stable identity, and make completion plus acknowledgement recoverable.",
    "An empty provider search during its five-second lag cannot certify absence, and reference is explicitly nonunique.",
    "The 24-hour key expiration prevents an unrestricted exactly-one-charge guarantee for arbitrarily delayed retries using only the supplied contract.",
    "Identify a meaningful added guarantee or restriction, such as durable unique provider reference/indefinite deduplication, a bounded recovery window plus controlled manual reconciliation, while acknowledging how that changes the requested guarantee."
], ["Do not assert local rollback undoes a provider charge.", "Do not present a pending flag alone as proof that charging occurred.", "Do not import real-provider behavior."],
["Claims a local unique constraint makes the external effect exactly once.", "Claims the existing stable key guarantees deduplication after 24 hours.", "Recommends blind new-key retries after an ambiguous result as safe."],
constraints={"language":"Spanish"}, source_ids=["A06-PROVIDER", "A06-CONSUMER", "A06-TRACE", "A06-PROPOSALS"], complexity_features=["crash at transaction boundary", "at-least-once delivery", "bounded external idempotency", "eventual search consistency"],
source_expectations=["Use the invented provider contract as authoritative and cite its evidence ID for retention and search limitations."], verification=["Executable dictionary-based provider model checks 1400 cents for attempt keys and 700 cents for stable within-retention key."])


a07_messages = [(41,1,6),(42,2,8),(41,2,9),(42,1,7)]
fence_token, value, accepted = 40, 0, []
for token, sequence, new in a07_messages:
    if token >= fence_token:
        fence_token, value = token, new
        accepted.append(True)
    else:
        accepted.append(False)
check("A07", "token-only acceptance", accepted, [True,True,False,True])
check("A07", "token-only final value", value, 7)
revision, value, accepted = (40,0), 0, []
for token, sequence, new in a07_messages:
    if (token,sequence) > revision:
        revision, value = (token,sequence), new
        accepted.append(True)
    else:
        accepted.append(False)
check("A07", "revision acceptance", accepted, [True,True,False,False])
check("A07", "revision final value", value, 8)
add("A07", "distributed_leases_fencing_and_in_generation_order", '''
This is an original synthetic distributed-storage exercise. The lock service and storage rules are defined here, so the question is about reasoning from a protocol rather than naming a particular vendor. We need to explain an incident to engineers who have correctly learned that leases expire but have assumed that expiration also retracts every network request a former leader has already sent.

[A07-LEASE] Acquiring a lease for resource X returns a strictly increasing integer token. A valid lease holder may issue writes while it believes its lease is valid. The lock service never grants overlapping leases according to its own clock, but clients can pause, networks can delay messages, and a storage server does not consult the lock service on every write. Token 41 was granted to worker A; after its lease expired, token 42 was granted to worker B. These tokens concern the same resource. There are no token wraparounds or reused generations.

[A07-STORAGE] The current storage implementation keeps max_token and value for each resource. A write with token smaller than max_token is rejected; a write with token greater than or equal to max_token is accepted atomically, setting max_token to that token and replacing value. The server ignores the accompanying sequence field. Repeating an accepted write may produce another successful response, and responses themselves can be lost. Initial state for X is max_token=40 and value=0.

[A07-ARRIVALS] These are storage arrival order, not send order:

| Arrival | Worker | Token | Sequence within worker's generation | Value |
|---|---|---:|---:|---:|
| 1 | A | 41 | 1 | 6 |
| 2 | B | 42 | 2 | 8 |
| 3 | A | 41 | 2 | 9 |
| 4 | B | 42 | 1 | 7 |

Worker B intentionally issued sequence 1 before sequence 2, but the messages were reordered in transit. Sequence numbers are assigned once and stay attached to a command on retry. All values here are complete replacements, not increments. The business rule is that commands from a newer token supersede all commands from older tokens, and within one token the larger sequence supersedes smaller sequences. A retry of an already applied identical command should not change the value or be reported as a new business change.

[A07-REVIEW] One engineer says leases alone make arrival 3 impossible. Another says the implemented fencing check fixes every stale-write problem, so final value must be 8. A third proposes rejecting every write whose token is equal to max_token, which would allow only the first command from each leader generation. We want to repair the actual rule rather than accidentally prohibit a legitimate leader from making several updates.

Explain the outcome of every arrival under the current implementation and determine final value. Separate the old-leader problem from reordering within a current generation. Propose an atomic storage acceptance rule that meets the stated ordering and retry requirements, including what it does with an equal revision carrying a different payload. Discuss where the remembered revision must live and why merely comparing local client clocks or checking the lease before sending does not enforce the same guarantee. Finally, state what your correction establishes about ordering and what it does not establish about delivery or eventual progress during a long network partition.
''', [
    "Current storage accepts arrivals 1, 2, and 4, rejects arrival 3, and ends with max_token 42 and value 7.",
    "Lease expiry does not retract already sent messages, so delayed arrival 3 remains possible.",
    "Fencing rejects older generations only when the resource server atomically enforces the token check.",
    "Equal token acceptance allows the sequence-1 command to overwrite sequence 2 in the current protocol.",
    "A lexicographic revision of token then sequence, stored and compared atomically with the value, accepts genuinely newer commands and rejects older commands; this trace then ends at value 8.",
    "For an equal revision and identical payload, return the prior outcome/no-op; for an equal revision with a different payload, reject a protocol conflict rather than silently overwrite.",
    "Keep the revision durably at the authority that applies the resource write; a client-side time check does not prevent delayed application.",
    "Ordering safety does not guarantee delivery, bounded latency, or progress under a partition; rejecting all equal tokens would also reject legitimate later commands in a generation."
], ["Do not assume synchronized client clocks or impossible delayed packets.", "Do not treat increasing token as increasing sequence within the token."],
["Claims current final value is 8.", "Says a lease makes delayed old-leader storage writes impossible.", "Proposes accepting equal revision with changed payload as an idempotent retry."],
source_ids=["A07-LEASE", "A07-STORAGE", "A07-ARRIVALS", "A07-REVIEW"], complexity_features=["two ordering dimensions", "atomic server enforcement", "retry conflict", "safety versus liveness"],
source_expectations=["Explicitly use the storage contract rather than assuming an unstated lease check exists."], verification=["Executed both token-only and lexicographic-revision simulations."])


maxima = {"p0":0, "p1":0}
active = {"p0","p1"}
watermark = -10
total, emitted, purged = 0, False, False
a08_steps = [
    ("data","p0",20,5),("data","p1",50,7),("heartbeat","p0",80,0),
    ("heartbeat","p1",75,0),("data","p0",40,3),("idle","p1",None,0),
    ("heartbeat","p0",100,0),("data","p1",55,4)]
a08_trace=[]
for kind,p,ts,v in a08_steps:
    event=[]
    if kind == "idle": active.remove(p)
    else:
        active.add(p)
        if kind == "data":
            if watermark >= 80:
                event.append("drop")
            else:
                total += v
                if emitted: event.append("correction:"+str(total))
        maxima[p] = max(maxima[p],ts)
    watermark = max(watermark, min(maxima[p]-10 for p in active))
    if not emitted and watermark >= 60:
        emitted=True; event.append("initial:"+str(total))
    if not purged and watermark >= 80:
        purged=True; event.append("purge")
    a08_trace.append({"watermark":watermark,"actions":event})
check("A08", "watermark sequence", [x["watermark"] for x in a08_trace], [-10,10,40,65,65,70,90,90])
check("A08", "outputs and purge", [x["actions"] for x in a08_trace], [[],[],[],["initial:12"],["correction:15"],[],["purge"],["drop"]])
add("A08", "streaming_watermarks_lateness_and_idle_partitions", '''
This is an original synthetic stream-processing protocol, not a question about defaults in any named framework. Our dashboard shows a preliminary minute total and occasionally a correction. A manager wants to call the first result final because the wall clock is already past the minute, while an engineer wants to keep every window forever because a disconnected partition can eventually return. Help us explain what our explicitly chosen rules actually guarantee.

[A08-RULES] There are two partitions, p0 and p1. Each begins active with maximum observed event timestamp zero. Event timestamps are seconds from a shared origin. For each active partition, its proposed watermark is its maximum observed timestamp minus 10. The global watermark is the minimum proposed watermark over active partitions, but it is monotonic: if recomputation gives a smaller value, the existing global watermark stays unchanged. Initially it is -10. A heartbeat advances a partition's maximum timestamp but contributes no amount. An idle control excludes a partition from the minimum. Its next data message reactivates it; maxima never decrease.

For a data message, first judge and add its amount using the current global watermark. Then update that partition's maximum timestamp and recompute the watermark. For a heartbeat or idle control, update control state and recompute directly. The window [0,60) includes event times at least zero and less than 60. Its initial result is emitted when the watermark first reaches or exceeds 60. Once emitted, an accepted data message for that window produces a replacement total immediately. While watermark is below 80, such data is still accepted. On reaching 80 or more, delete the window state permanently; subsequent records for it are dropped and counted. Controls do not themselves create corrections. These rules fully specify boundary behavior.

[A08-INPUT] Process these messages in arrival order:

| Step | Message |
|---|---|
| 1 | p0 data, event time 20, amount 5 |
| 2 | p1 data, event time 50, amount 7 |
| 3 | p0 heartbeat, timestamp 80 |
| 4 | p1 heartbeat, timestamp 75 |
| 5 | p0 data, event time 40, amount 3 |
| 6 | mark p1 idle |
| 7 | p0 heartbeat, timestamp 100 |
| 8 | p1 data, event time 55, amount 4 |

[A08-DOWNSTREAM] A consumer currently adds every emitted number to its database. It receives only a window identifier and total, not an increment flag. The transport may redeliver the same emitted message. For this exercise, wall-clock processing times do not affect any rule, and there are no further messages after step 8.

Please work through the watermark and the fate of the [0,60) window after each step. Explain why the event at step 5 can change an already emitted result, why excluding an idle partition allows progress, and what reactivation at step 8 can and cannot reverse. Give the emitted totals and the final disposition of the amount 4. Then assess whether the downstream addition rule is correct and describe enough output identity/version semantics to make corrections and redelivery safe. Finally, explain what the chosen late-data policy trades away and whether the first emission or state deletion proves that the physical world will never produce another relevant event.
''', [
    "The watermarks after steps 1–8 are -10, 10, 40, 65, 65, 70, 90, 90.",
    "The initial window total 12 is emitted at step 4 when watermark reaches 65.",
    "Step 5 is accepted while watermark is 65 and emits replacement total 15.",
    "Idle p1 is removed from the minimum at step 6, allowing watermark 70, then step 7 reaches 90 and permanently purges the window.",
    "Reactivation cannot lower the monotonic watermark; step 8 is dropped, so amount 4 never enters this window's emitted total.",
    "Adding 12 and 15 double-counts replacement totals; downstream should upsert by window and a suitable revision/event identity with stale-update and duplicate handling.",
    "A useful versioning design distinguishes redelivery of one emission from a newer correction and prevents an older replacement arriving later from reverting the total.",
    "Watermarks and allowed lateness are a processing policy with bounded state and possible loss of very late data, not proof that no future physical event can arrive."
], ["Do not import framework-specific watermark defaults.", "Do not use wall-clock time to override the supplied event-time protocol."],
["Adds the step-8 amount after purge.", "Moves the watermark backward on reactivation.", "Treats both emitted totals as independent increments."],
source_ids=["A08-RULES", "A08-INPUT", "A08-DOWNSTREAM"], complexity_features=["explicit state machine", "monotonic minimum", "late corrections", "versioned downstream replacement"],
source_expectations=["Use A08-RULES for every timing boundary and distinguish the downstream transport assumption from window arithmetic."], verification=["Executed the supplied eight-step state machine and asserted watermarks, emissions, purge, and drop."])


a09_both_true = 10000*.02*.72
a09_both_false = 10000*.98*.04
check("A09", "expected both-positive true cases", a09_both_true, 144.0)
check("A09", "expected both-positive false cases", a09_both_false, 392.0)
check("A09", "both-positive posterior", a09_both_true/(a09_both_true+a09_both_false), 18/67, 1e-12)
check("A09", "A-only posterior", (.02*.90)/(.02*.90+.98*.10), 9/58, 1e-12)
check("A09", "A positive B negative posterior", (.02*.18)/(.02*.18+.98*.06), 3/52, 1e-12)
check("A09", "incorrect independence posterior", (.02*.9*.8)/(.02*.9*.8+.98*.1*.05), 144/193, 1e-12)
add("A09", "probability_correlated_diagnostic_evidence", '''
This is an original synthetic quality-control exercise about detecting defective machine parts, not medical advice. A screening program uses two automated detectors, A and B. Management wants to combine their results and has asked for an explanation they can use when deciding which parts need expensive manual inspection. All probabilities below describe the same stable incoming population and the same operating conditions. Assume the supplied rates are known exactly for the arithmetic; sampling uncertainty is a separate future issue.

[A09-BASE] Two percent of incoming parts are defective. A typical shipment contains 10,000 independently sampled parts. Defect status is the target of the decision, not whether a detector happened to fire. Detector B is usually run only when A is positive, but its joint behavior was measured in a separate complete-label validation study that ran both detectors on every selected part.

[A09-JOINT] These are joint conditional probabilities within each true-status group:

| Outcome | Given defective | Given not defective |
|---|---:|---:|
| A positive, B positive | 0.72 | 0.04 |
| A positive, B negative | 0.18 | 0.06 |
| A negative, B positive | 0.08 | 0.01 |
| A negative, B negative | 0.02 | 0.89 |

Each column sums to one. Both detectors analyze some of the same surface features, so there is no claim of conditional independence. The validation study was representative within each true-status group, making its conditional probabilities applicable to the incoming population. Running B only after A does not change a part's underlying detector outcomes; it changes which outcomes the production system observes.

[A09-MEMO] An analyst extracted marginal sensitivity 90 percent and false-positive rate 10 percent for A, and marginal sensitivity 80 percent and false-positive rate 5 percent for B. The memo multiplies the two false-positive rates, multiplies the two sensitivities, and concludes that a doubly positive part is roughly three-quarters likely to be defective. It then calls B a “sixteen-fold confirmation” because 0.80 divided by 0.05 is sixteen. A second analyst says the correlated detectors provide literally no extra information, so a doubly positive part should be treated exactly like a part that is merely A-positive.

Please explain which claims follow from the supplied table. Calculate expected true-defective and nondefective counts among doubly positive parts in the 10,000-part shipment, and the probability that a doubly positive part is defective. Compare it with the probability after A alone and with the probability after A-positive/B-negative. Show why applying B inside the already A-positive subset requires the conditional rates within that subset, and determine B's positive likelihood ratio there. We need enough arithmetic to locate the memo's error, not just a warning that correlation exists.

Finally, explain why the numerical answer is not itself an automatic inspection threshold. The cost of a missed defect, unnecessary inspection, and available capacity have not been supplied. Say what information is still needed to turn these probabilities into a policy, and identify which population or validation assumptions would have to be revisited if the incoming defect rate or detector behavior changed.
''', [
    "Expected doubly positive counts are 144 defective and 392 nondefective, totaling 536.",
    "The doubly positive posterior is 144/536, approximately 26.87 percent.",
    "After A alone the posterior is 180/(180+980), approximately 15.52 percent; A-positive/B-negative is 36/(36+588), approximately 5.77 percent.",
    "The memo's roughly 74.61 percent result comes from assuming joint false positives 0.10×0.05 rather than the supplied 0.04.",
    "Within A-positive parts, B is positive with probability 0.72/0.90=0.80 for defective and 0.04/0.10=0.40 for nondefective, giving a positive likelihood ratio of 2, not 16.",
    "Correlation does not mean no new information; B changes the posterior in this table.",
    "Distinguish expected shipment counts from a guarantee about realized integer counts.",
    "Inspection decisions need costs/capacity or another objective; transfer requires the stated base rate and applicable conditional detector distributions."
], ["Do not multiply marginal false-positive rates without the missing independence assumption.", "Do not present a posterior as a certainty about an individual part."],
["Endorses approximately 75 percent as the correct posterior.", "Claims B provides no information after A.", "Uses the marginal likelihood ratio 16 inside the selected A-positive group."],
source_ids=["A09-BASE", "A09-JOINT", "A09-MEMO"], complexity_features=["base-rate weighting", "conditional dependence", "selection by first test", "probability versus decision"],
source_expectations=["Attribute all numerical rates to the synthetic table; no real-world detector claims are warranted."], verification=["Executed exact arithmetic for all expected counts, posteriors, and the incorrect-independence comparison."])


check("A10", "old aggregate", (144+6)/(180+20), .75)
check("A10", "new aggregate", (18+72)/(20+180), .45)
check("A10", "old standardized equal weights", .5*(144/180)+.5*(6/20), .55)
check("A10", "new standardized equal weights", .5*(18/20)+.5*(72/180), .65)
check("A10", "future old standardization", .2*.8+.8*.3, .40, 1e-12)
check("A10", "future new standardization", .2*.9+.8*.4, .50, 1e-12)
add("A10", "statistics_simpson_reversal_and_causal_scope", '''
This is an original synthetic operations-study packet. A service team introduced a new workflow and wants to decide whether to roll it out. Both sides of an internal debate have found a percentage that supports their preferred story. Please help us distinguish arithmetic facts, comparable descriptive summaries, and the causal conclusion that the decision would actually require.

[A10-DATA] The outcome is completing a case within seven calendar days. All cases have complete follow-up, the definition of completion stayed constant, and there are no missing outcomes. Complexity was classified before any workflow was assigned. Counts are:

| Workflow | Pre-existing complexity | Completed within seven days | Total cases |
|---|---|---:|---:|
| Old | Easy | 144 | 180 |
| Old | Hard | 6 | 20 |
| New | Easy | 18 | 20 |
| New | Hard | 72 | 180 |

[A10-ASSIGNMENT] This was not a randomized experiment. The scheduling manager routed most hard cases to the new workflow because that team had extra capacity. Within each complexity group, the manager also preferred sending urgent cases to a specialist who worked exclusively with the new workflow. Urgency is not recorded in this table and can affect completion. There may also be individual staff differences. We know complexity preceded treatment, but that alone does not establish that complexity captures every common cause of workflow choice and outcome.

[A10-PLANNING] The rollout committee asks for two descriptive summaries under explicitly chosen case mixes. One uses half easy and half hard cases to make the two workflows directly comparable on the recorded complexity variable. The second uses the expected next-quarter case mix, 20 percent easy and 80 percent hard. For these descriptive calculations, assume the observed stratum-specific completion rates remain the rates being summarized. This is a calculation convention, not a claim that a future intervention leaves those rates unchanged.

[A10-CLAIMS] The director says the new workflow is harmful because its overall completion rate is 30 percentage points lower. The implementation lead says the new workflow is proven to improve every patient's outcome because it has a higher rate in both complexity groups. The analyst recommends “averaging the four percentages,” but has not said which population that average is supposed to describe. This is a service-case example; the director's patient wording is simply an inaccurate phrase in the internal note, not an extra dataset.

Explain how both within-group improvements and an overall decline can be true simultaneously. Calculate the two raw workflow rates, the two within-group contrasts, and both requested pairs of standardized rates. State the weights used in each calculation and the population each summary is meant to describe. Then assess all three claims, including what would be wrong with calling the observed adjusted difference the proven effect of switching a particular case to the new workflow.

Finally, recommend what additional design or evidence would most directly reduce the uncertainty about a rollout decision. A proposal should address the unrecorded routing and staffing differences rather than merely ask for a larger copy of the same table. Explain whether random assignment within complexity strata, measuring relevant pre-assignment variables, or separating the specialist effect from the workflow effect would answer the same or different questions. We need a defensible interpretation of these numbers, not a slogan that all aggregate comparisons are invalid.
''', [
    "Raw completion is 75 percent for old and 45 percent for new, a new-minus-old difference of -30 percentage points.",
    "Within easy cases rates are 80 versus 90 percent, and within hard cases 30 versus 40 percent; both contrasts favor new by 10 percentage points.",
    "Explain differing case-mix weights: old is 90 percent easy whereas new is 90 percent hard, producing the aggregation reversal.",
    "Equal-complexity standardization yields old 55 percent and new 65 percent.",
    "The future 20/80 case-mix standardization yields old 40 percent and new 50 percent.",
    "These are chosen descriptive standardizations; their interpretation depends on the target population and does not establish individual-level improvement or causal identification.",
    "Routing by unmeasured urgency and specialist/staff differences can confound within-complexity comparisons, so neither the raw decline nor adjusted advantage alone proves a workflow effect.",
    "Recommend a design or measurement strategy addressing assignment, such as randomization within complexity and staff or a factorial/separated staffing comparison, while distinguishing the package effect from workflow-only effect."
], ["Do not infer everyone benefits from higher group averages.", "Do not say changing weights automatically removes all confounding."],
["Claims the new workflow is causally harmful or beneficial based solely on this table.", "Computes standardized rates using each workflow's own case mix.", "Treats pre-treatment measurement of one variable as proof of exchangeability."],
source_ids=["A10-DATA", "A10-ASSIGNMENT", "A10-PLANNING", "A10-CLAIMS"], complexity_features=["Simpson reversal", "two target populations", "unmeasured confounding", "intervention estimand"],
source_expectations=["Use A10-ASSIGNMENT when qualifying causal claims and A10-PLANNING when selecting weights."], verification=["Executed raw and standardized arithmetic for both target populations."])


check("A11", "median standard x0", math.exp(4), 54.598150033144236, 1e-12)
check("A11", "median accelerated x0", math.exp(3.9), 49.40244910553017, 1e-12)
check("A11", "median ratio x0", math.exp(-.1), .9048374180359595, 1e-12)
check("A11", "median ratio x1", math.exp(-.25), .7788007830714049, 1e-12)
check("A11", "mean ratio x0", math.exp(-.1+(.8**2-.4**2)/2), math.exp(.14), 1e-12)
check("A11", "mean ratio x1", math.exp(-.25+(.8**2-.4**2)/2), math.exp(-.01), 1e-12)
add("A11", "statistics_log_model_interaction_and_retransformation", '''
This is an original synthetic performance-model review. Our team modeled render duration for a graphics service, and the presentation mixes milliseconds, seconds, percentages, and average user experience. Please help us understand exactly what the fitted model says before we publish the chart. Treat the numerical model and residual assumptions as exact for this exercise; we are evaluating interpretation, not fitting a new model or estimating coefficient uncertainty.

[A11-MODEL] The response is ln(T), where T is duration in seconds and ln is the natural logarithm. The model is

ln(T) = 4.00 + 0.20 x - 0.10 z - 0.15 xz + epsilon,

where x = (file_size_MiB - 100)/100 and z is 1 for accelerated mode and 0 for standard mode. Thus x=0 means a 100 MiB file, and increasing x by one means adding 100 MiB. Conditional on x and z, epsilon has mean zero and a normal distribution. Its standard deviation is 0.40 for standard mode and 0.80 for accelerated mode. File sizes in the observed dataset lie between 100 and 200 MiB. There is no assertion that the fitted relationship continues outside that range.

[A11-IDENTITY] You may use the lognormal identity: if ln(T) is normal with mean mu and variance sigma squared, then the conditional median of T is exp(mu), while its conditional arithmetic mean is exp(mu + sigma squared/2). The residual variance is not an extra coefficient to add to ln(T) for an individual observation. The displayed regression coefficient estimates describe the fitted conditional distribution; they are not already converted into seconds or percentages.

[A11-SLIDE] The draft slide says: “Acceleration saves 0.10 seconds for every file. The interaction saves a further 15 percent for each additional MiB. Exponentiating the regression prediction gives average time, so acceleration is faster on average at every size. The coefficient proves that switching on the feature causes this improvement.” The author chose this wording because the z coefficient is negative and all of the model's conditional medians for accelerated mode are smaller than the corresponding standard-mode medians in the observed size range.

[A11-STUDY] Users chose whether to enable acceleration. The service recorded file size and mode, but did not record graphics-card quality, model complexity, or whether a user had previously retried a slow request. Those factors could influence both mode selection and render duration. There was no randomized rollout. The product team cares about both the typical request and total machine-seconds consumed by a large batch, so the distinction between median and arithmetic mean is operationally relevant.

Please correct the slide's interpretation. Compare the modes for 100 MiB and 200 MiB files, giving median ratios or percentage changes and enough numerical durations to make the units concrete. Explain the size slope within each mode and what the interaction changes. Then calculate the arithmetic-mean ratio at both sizes using the supplied residual distributions, and explain how the ordering of means can differ from the ordering of medians. Finally, state the causal and extrapolation limits of this evidence and suggest what study would answer the feature-switching question more directly.
''', [
    "At 100 MiB the median log difference is -0.10, so accelerated/standard median ratio is exp(-0.10)=0.90484, about 9.52 percent lower; medians are about 49.40 and 54.60 seconds.",
    "At 200 MiB the median log difference is -0.25, giving ratio 0.77880, about 22.12 percent lower; medians may be reported as about 51.94 versus 66.69 seconds.",
    "The within-mode log-duration slope per additional 100 MiB is 0.20 for standard and 0.05 for accelerated; no coefficient is a fixed saving in seconds per MiB.",
    "The interaction modifies the mode contrast as size changes; it is not a standalone 15 percent per MiB effect.",
    "Distinguish exponentiated fitted log mean, which is the conditional median under the supplied model, from the arithmetic mean requiring the variance term.",
    "The accelerated/standard arithmetic-mean ratio at 100 MiB is exp(0.14)=1.15027, so accelerated has a roughly 15.03 percent higher mean despite a lower median.",
    "At 200 MiB the arithmetic-mean ratio is exp(-0.01)=0.99005, about 1.00 percent lower; larger accelerated residual variance explains the difference from median comparisons.",
    "Mode self-selection and unmeasured factors prevent a causal conclusion, and results beyond 100–200 MiB are extrapolations; a randomized mode comparison or appropriately designed rollout would more directly address causality."
], ["Do not interpret a log coefficient as seconds.", "Do not assume equal residual variances.", "Do not ignore the MiB centering and 100 MiB scale."],
["Calls exp(mu) the arithmetic mean under the supplied nonzero-variance model.", "Claims acceleration has a lower conditional mean at 100 MiB.", "Claims the observational coefficient proves a causal feature effect."],
source_ids=["A11-MODEL", "A11-IDENTITY", "A11-SLIDE", "A11-STUDY"], complexity_features=["centered scaled predictor", "interaction", "lognormal retransformation", "mean-median reversal", "observational identification"],
source_expectations=["Use the supplied lognormal identity and residual variances explicitly; use A11-STUDY for the causal qualification."], verification=["Executed exponential ratios and mode-specific variance correction arithmetic."])


a12_before=[100,102,98,150,152,148]
a12_after=[96,99,94,147,149,144]
a12_d=[b-a for a,b in zip(a12_before,a12_after)]
a12_mean=statistics.mean(a12_d)
a12_sd=statistics.stdev(a12_d)
a12_se=a12_sd/math.sqrt(6)
a12_margin=2.570582*a12_se
check("A12", "paired differences", a12_d, [-4,-3,-4,-3,-3,-4])
check("A12", "paired mean", a12_mean, -3.5)
check("A12", "paired standard error", a12_se, math.sqrt(.05), 1e-12)
check("A12", "paired interval lower", a12_mean-a12_margin, -4.074799606441693, 1e-7)
check("A12", "paired interval upper", a12_mean+a12_margin, -2.925200393558307, 1e-7)
check("A12", "independent-formula standard error", math.sqrt(statistics.variance(a12_before)/6+statistics.variance(a12_after)/6), 15.907545379473227, 1e-12)
add("A12", "statistics_pairing_uncertainty_and_before_after_design", '''
This is an original synthetic laboratory-performance study. Please answer in French. Six machines were each measured once before and once after a software patch. We are trying to understand why two analyses have the same estimated average change but radically different uncertainty intervals, and whether either analysis justifies a broad causal statement about the patch. The measurements are elapsed seconds for a fixed workload; lower is better.

[A12-DATA]

| Machine identifier | Before patch | After patch |
|---|---:|---:|
| M1 | 100 | 96 |
| M2 | 102 | 99 |
| M3 | 98 | 94 |
| M4 | 150 | 147 |
| M5 | 152 | 149 |
| M6 | 148 | 144 |

Identifiers genuinely link the same physical machine across measurements. The first three machines are one hardware family and the last three another. No machine is missing a measurement, no row is duplicated, and there is no claim that the twelve observations came from twelve separate machines. All six machines are treated as independent units for the requested calculation, while the two observations from a machine can be strongly correlated.

[A12-METHOD] For a conventional paired interval, define each difference as after minus before. Use the sample standard deviation of the six differences, divide it by the square root of six to obtain the standard error, and use t critical value 2.570582 for a two-sided nominal 95 percent interval with five degrees of freedom. For comparison, the unpaired spreadsheet used square root of (sample variance before divided by six plus sample variance after divided by six) as its standard error. You need not compute an unpaired t critical value. These methods are supplied so that a disagreement about software defaults does not distract from the structure of the data.

[A12-CONTEXT] Every before measurement occurred in the morning and every after measurement in the afternoon. The room cooling system was recalibrated at noon, and the workload might also benefit from caches warmed by the first run. Machines were chosen for convenience from the lab's available inventory. There was no simultaneous untreated group and no randomization of measurement order. The team can rerun the experiment and has enough machines to assign patch order within hardware family.

[A12-CLAIMS] One analyst says the unpaired analysis is safer because ignoring the machine identifiers avoids assuming a correlation. Another says the paired interval proves that 95 percent of individual future machines will improve by the interval's amount. The project lead says the narrow interval proves the patch, rather than the cooling or warm-up, caused the reduction. They also propose reporting six percentages and averaging them as if this were necessarily the same estimand as the average change in seconds.

Explain the two standard errors using these data. Give the signed differences, their mean, the paired standard error, and the paired interval, then interpret that interval carefully. Explain why pairing can remove large between-machine differences without removing a common time-of-day change. Assess the claims about safety, future individual machines, causal attribution, and averaging percentages. Recommend an experiment that preserves useful pairing or blocking while distinguishing the patch from order and environmental effects. Organize the response under Calculs and Interprétation, but choose whatever detail is needed within those sections.
''', [
    "Answer in French with the requested two section headings or equivalent exact headings Calculs and Interprétation.",
    "After-minus-before differences are -4,-3,-4,-3,-3,-4 seconds, with mean -3.5 seconds.",
    "Sample variance of differences is 0.3, sample standard deviation about 0.5477, and paired standard error about 0.2236 seconds.",
    "The supplied t interval is approximately [-4.0748,-2.9252] seconds.",
    "The unpaired-formula standard error is about 15.91 seconds because it retains the large hardware-level between-machine variation and ignores the strong pairing.",
    "Interpret the interval as uncertainty in an average difference under the inferential assumptions, not a 95 percent prediction interval or a guarantee for 95 percent of individual machines.",
    "Pairing does not separate patch effect from the common afternoon cooling/warm-up changes, and the convenience sample limits generalization.",
    "A mean percentage change is a different estimand from a mean absolute change; propose randomized order/crossover with carryover controls or randomized treated and control comparisons blocked by hardware, addressing the concrete confounders."
], ["Do not treat before and after as independent samples merely because they occupy separate columns.", "Do not interpret the interval as a distribution of individual improvements."],
["Claims the narrow paired interval establishes the patch's causal effect despite the supplied concurrent changes.", "Computes paired uncertainty from the raw before/after dispersion.", "Reverses the sign without making its convention explicit."],
constraints={"language":"French"}, source_ids=["A12-DATA", "A12-METHOD", "A12-CONTEXT", "A12-CLAIMS"], complexity_features=["dependent measurements", "large nuisance variance", "confidence versus prediction", "causal confounding", "estimand choice"],
source_expectations=["Use the supplied critical value rather than silently substituting a normal critical value; qualify causal conclusions with A12-CONTEXT."], verification=["Executed paired and independent-formula variances, standard errors, and interval arithmetic."])


check("A13", "twenty independent null tests at least one false positive", 1-.95**20, .6415140775914581, 1e-12)
check("A13", "Bonferroni threshold", .05/20, .0025)
check("A13", "Bonferroni adjusted smallest p", min(1,.018*20), .36)
check("A13", "unjustified eighty-independent-tests comparison", 1-.95**80, .9834846256149864, 1e-12)
add("A13", "statistics_multiplicity_selection_and_optional_stopping", '''
This is an original synthetic product-experiment review. A team tested a recommendation feature and found one metric with a nominal p-value below 0.05. They want to announce a confirmed improvement, while the analyst who inherited the study thinks the report combines several different inferential problems. Please explain what can be calculated from the information given and where the missing design information prevents a numerical conclusion.

[A13-PLAN] At the final analysis, the team considered twenty distinct outcome metrics. For one explicitly hypothetical calculation, assume all twenty null hypotheses are true, each final-analysis p-value is exactly uniform on [0,1], and those twenty final p-values are independent. The decision rule in that hypothetical calculation is to declare a discovery if at least one p-value is below 0.05. This independence assumption is supplied only for that calculation; it does not automatically apply to interim looks at accumulating observations.

[A13-RESULTS] In the actual report, the smallest final p-value is 0.018 for average saved clicks per session. The second smallest is 0.041 for a differently defined engagement metric. Every other final p-value is at least 0.12. The saved-click estimate is +0.8 clicks per session, but no variance, standard error, or confidence interval was retained in the packet. There is no prespecified primary outcome in the study record. A saved-click increase may or may not be practically useful depending on whether it represents real saved effort; the study did not measure task completion time.

[A13-LOOKS] The dashboard was also inspected at four interim sample sizes before the final analysis, using the same accumulating participants. The team could stop or continue depending on what it saw. Neither a sequential testing rule nor an alpha-spending plan was specified. We do not have the joint distribution of those repeated p-values, the exact stopping decisions, or the dashboard snapshots. The final twenty-outcome independence assumption does not supply those missing facts.

[A13-DRAFT] The announcement says: “p=0.018 means there is only a 1.8 percent chance that the feature has no effect. Since the best metric is significant, the twenty-metric search adds no uncertainty. If there were a problem, collecting more data until the result becomes significant again would fix it.” A reviewer correctly objects to multiplicity but then claims the exact overall false-positive probability is 1 minus 0.95 to the power of 100, treating five looks times twenty outcomes as one hundred independent tests without further justification.

Please compute the false-positive probability for the clearly specified twenty-test hypothetical experiment and the Bonferroni threshold for controlling that family's error rate at 0.05. Say whether either reported p-value passes that threshold and what a simple Bonferroni-adjusted value for the smallest p-value would be. Then distinguish this valid calculation from the unquantified additional effect of the actual optional stopping.

Correct the interpretation of the p-value and explain why selection can distort an apparent effect estimate as well as the announcement's certainty. Recommend a concrete confirmatory follow-up with an outcome, stopping rule, and decision criterion decided before observing its results. Address practical importance and uncertainty without fabricating the missing confidence interval or treating statistical significance as a complete product decision.
''', [
    "Under the specified twenty-independent-null-test hypothetical, the probability of at least one false positive is 1-0.95^20, about 64.15 percent.",
    "Bonferroni per-test threshold is 0.0025; neither 0.018 nor 0.041 passes, and the smallest simple adjusted p-value is 0.36.",
    "A p-value is a tail probability under a null model and specified analysis, not the posterior probability the null is true.",
    "The twenty-final-test calculation does not quantify the actual optional-stopping design; dependence and unspecified stopping prevent the reviewer's claimed exact 100-test probability.",
    "Bonferroni across the final twenty outcomes alone does not retroactively repair arbitrary invalid p-values caused by unaccounted sequential selection.",
    "Selecting a favorable metric/estimate can exaggerate apparent effects; the retained +0.8 alone cannot determine its confidence interval or practical benefit.",
    "A useful confirmation prespecifies a meaningful primary outcome or controlled family, sample size or valid sequential stopping rule, and analysis before fresh data are inspected.",
    "Decision-making should consider uncertainty and a practical effect criterion or direct effort outcome, not merely whether any p-value crosses 0.05."
], ["Do not calculate an exact repeated-look error rate from unstated independence.", "Do not fabricate a confidence interval from the effect estimate and p-value without a model/test specification."],
["Calls 0.018 a 1.8 percent probability that the null is true.", "Endorses repeated sampling until significance as automatically valid confirmation.", "Claims final-outcome Bonferroni alone fixes the unspecified optional stopping."],
source_ids=["A13-PLAN", "A13-RESULTS", "A13-LOOKS", "A13-DRAFT"], complexity_features=["multiple comparisons", "sequential dependence", "selective reporting", "missing uncertainty", "statistical versus practical criterion"],
source_expectations=["Clearly identify which assumptions belong only to A13-PLAN and which facts are missing under A13-LOOKS."], verification=["Executed family-error and Bonferroni arithmetic; no claim to have simulated the unspecified actual stopping mechanism."])


a14_times=[0,30,90,120]
a14_raw=[600,1100,600,100]
a14_power=[2*r-200 for r in a14_raw]
a14_hold=sum((a14_times[i+1]-a14_times[i])*a14_power[i] for i in range(3))
a14_trap=sum((a14_times[i+1]-a14_times[i])*(a14_power[i]+a14_power[i+1])/2 for i in range(3))
check("A14", "calibrated powers", a14_power, [1000,2000,1000,0])
check("A14", "hold integration joules", a14_hold, 180000)
check("A14", "hold energy Wh", a14_hold/3600, 50)
check("A14", "trapezoidal energy Wh", a14_trap/3600, 125/3, 1e-12)
check("A14", "unweighted mean energy Wh", statistics.mean(a14_power)*120/3600, 100/3, 1e-12)
check("A14", "counter difference kWh", 12.052-12.000, .052, 1e-12)
add("A14", "units_calibration_irregular_sampling_and_integration", '''
This is an original synthetic instrument-validation exercise. We measured an electrical load with an analog sensor and compared its calculated energy with a separate cumulative energy register. The spreadsheet currently combines an average, a unit conversion, and a rounding step, and the author cannot tell which discrepancy indicates a real problem. We need an explanation of the measurement model and the arithmetic before replacing any instrument.

[A14-CALIBRATION] The analog readings are millivolts. For this exercise the calibration is exact: instantaneous power in watts equals 2 times the reading in millivolts minus 200. The offset is part of the calibration, not an uncertainty estimate. Every timestamp is elapsed seconds from the same starting instant, with exact timing. The acquisition contract says the load is held constant at the most recently sampled calibrated power until the next timestamp. This is a zero-order-hold model, not a statement that values change linearly between samples.

[A14-SAMPLES]

| Elapsed seconds | Sensor millivolts |
|---:|---:|
| 0 | 600 |
| 30 | 1100 |
| 90 | 600 |
| 120 | 100 |

The target interval is exactly [0,120) seconds. The reading at 120 seconds documents the new level beginning at that boundary; it has no positive duration inside the requested interval. There are no unsampled transitions under the supplied hold assumption. A watt is a joule per second, one watt-hour is 3600 joules, and one kilowatt-hour is 1000 watt-hours.

[A14-SPREADSHEET] The author converts all four readings to watts, takes their unweighted arithmetic mean, multiplies by 120, and divides by 1000, labeling the result kilowatt-hours. A reviewer notices the missing hour conversion and fixes only that divisor. A second reviewer proposes trapezoidal integration because it is “always more accurate” than rectangles. Both reviewers include the endpoint value in the calculation without explaining what physical interpolation model they assume.

[A14-REGISTER] The separate register reads 12.000 kWh at the start and 12.052 kWh at the end. Each displayed reading is guaranteed within plus or minus 0.001 kWh of the true cumulative reading. No independence or probability distribution is given for these errors. For this exercise, use a conservative possible-error bound for their difference rather than assuming errors cancel or combining them by a root-sum-of-squares formula. No additional uncertainty is assigned to the analog calculation under the stated idealized model.

Please calculate the calibrated powers, energy for each interval, total energy in joules, watt-hours, and kilowatt-hours, and time-weighted mean power. Explain precisely why the spreadsheet and the first reviewer's partial repair remain wrong. Also calculate what trapezoidal integration would give and explain why that is a different assumption rather than automatically an improvement here.

Then compare the analog total with the register's observed increase and its conservative possible range. Does this packet establish an inconsistency between the instruments, and what would you say if the calibration or hold model were only approximations in a real installation? Distinguish the exact arithmetic conditional on a model from evidence that the model accurately represents the physical load, and avoid converting a worst-case error bound into an unsupported confidence level.
''', [
    "Calibrated powers are 1000, 2000, 1000, and 0 watts.",
    "Hold-model interval energies are 30000, 120000, and 30000 joules; total 180000 J = 50 Wh = 0.050 kWh.",
    "Time-weighted mean power is 1500 W over 120 seconds; unweighted sample mean is 1000 W and wrongly weights unequal-duration intervals and the endpoint.",
    "Dividing W·seconds by 1000 yields kilojoules, not kWh; fixing the unit conversion alone leaves incorrect sample weighting and gives only 33.333 Wh.",
    "Trapezoidal integration gives 150000 J = 41.6667 Wh, reflecting linear interpolation rather than the specified hold model.",
    "The register increase is 0.052 kWh with conservative error at most 0.002 kWh, giving possible true increase [0.050,0.054] kWh.",
    "The analog value lies at the lower bound, so the supplied bounds do not establish a contradiction.",
    "Do not equate exact conditional arithmetic with perfect real instrumentation; calibration/model uncertainty would need separate evidence, and the error bound is not a probabilistic confidence interval."
], ["Do not count the last reading as an extra positive-duration interval.", "Do not assume independent register errors or a probability distribution."],
["Reports the energy as 180 kWh or 180 Wh.", "Calls trapezoidal integration necessarily more accurate under the stated hold contract.", "Claims the 0.002 kWh gap proves failure despite the given bounds."],
source_ids=["A14-CALIBRATION", "A14-SAMPLES", "A14-SPREADSHEET", "A14-REGISTER"], complexity_features=["affine calibration", "irregular sampling", "integration model choice", "compound units", "worst-case uncertainty"],
source_expectations=["Use the hold contract for the primary calculation and the register bounds for the compatibility decision."], verification=["Executed both integration models, unweighted comparison, and counter-difference arithmetic."])


def a15_select(call, config, environment):
    selected = call.get("timeoutMs")
    if selected is None: selected = config.get("timeoutMs")
    if selected is None:
        try: selected = float(environment.get("QUILL_TIMEOUT_MS", "1500"))
        except ValueError: return {"sent":False,"reason":"invalid"}
    if not isinstance(selected,(int,float)) or not math.isfinite(selected) or selected <= 0 or int(selected)!=selected:
        return {"sent":False,"reason":"invalid"}
    return {"sent":True,"client_ms":int(selected),"header_ms":int(selected),"server_ms":min(int(selected),5000)}
check("A15", "request R1", a15_select({"timeoutMs":6000},{"timeout":30,"timeoutMs":2500},{"QUILL_TIMEOUT_MS":"4000"}), {"sent":True,"client_ms":6000,"header_ms":6000,"server_ms":5000})
check("A15", "request R2", a15_select({"timeout":1},{"timeout":30,"timeoutMs":2500},{"QUILL_TIMEOUT_MS":"4000"}), {"sent":True,"client_ms":2500,"header_ms":2500,"server_ms":2500})
check("A15", "request R3", a15_select({}, {"timeout":30}, {"QUILL_TIMEOUT_MS":"2s"}), {"sent":False,"reason":"invalid"})
add("A15", "technical_source_version_scope_and_configuration_precedence", '''
This is an original synthetic documentation packet for an invented product named Quill. None of these excerpts describes a real package, and no external product knowledge is needed. We have several apparently conflicting sources, a deployed client, and a server that applies its own limit. Please help an on-call engineer explain three requests without choosing whichever documentation page has the newest publication date.

[A15-OLD] Client guide for Quill JavaScript SDK 1.8, published January 2024: the client option timeout is expressed in seconds, with a default of 30. This guide describes SDK 1.x. It contains no timeoutMs field and no description of the 2.x compatibility mode.

[A15-MIGRATION] Migration note for SDK 2.0, published June 2024: ordinary 2.x configuration uses timeoutMs, a positive integer number of milliseconds. Legacy timeout is ignored unless legacyMode is explicitly enabled. When legacyMode is false, timeout is not converted and is not an alias. The deployment in this packet has legacyMode=false. Per-call timeoutMs overrides constructor timeoutMs, which overrides environment QUILL_TIMEOUT_MS, which overrides the client default of 1500 milliseconds.

[A15-IMPLEMENTATION] SDK 2.3.1 bundled-source extract, verified against the deployed build in October 2025: resolution selects the first non-nullish timeoutMs from call options and constructor config. If both are absent or null, it applies JavaScript Number to QUILL_TIMEOUT_MS, or to the string 1500 when the environment variable is absent. It rejects a nonfinite, noninteger, or nonpositive result before making any network request. It uses the chosen integer for the local client wait timer and sends that same integer as the x-deadline-ms header. The deployed code has no duration-string parser and no legacy-mode override enabled.

[A15-SERVER] Server protocol 2.4, deployed September 2025: x-deadline-ms is a positive integer in milliseconds, and the effective server computation budget is the smaller of that value and 5000. If the header is absent the server budget is 1000 milliseconds. The budget starts when computation begins on the server. Network transit and response delivery consume additional wall time. The server sends a structured deadline error when its computation budget expires.

[A15-LATEST] Website guide updated November 2026, labeled SDK 3.x: duration strings such as 2s are accepted and the default is 2000 milliseconds. This document has not been backported to 2.x and the deployment has not been upgraded.

[A15-REQUESTS] R1 uses constructor {timeout:30, timeoutMs:2500}, environment QUILL_TIMEOUT_MS=4000, and call option {timeoutMs:6000}. R2 uses the same constructor and environment but call option {timeout:1}. R3 uses constructor {timeout:30}, environment QUILL_TIMEOUT_MS=2s, and no call options. An R1 trace reports a server deadline error received 5030 milliseconds after the client started waiting. No other trace is available, and none of the option values is dynamically changed during resolution.

Explain the effective client timer, transmitted header, and server budget for each request, or explain why no request is sent. Decide whether the R1 trace contradicts the specified limits. Identify which sources govern the disputed units, precedence, parsing, and server cap, and which are out of scope. Give a concrete configuration change for a two-second budget on this deployed version. Keep your answer within 350 words and cite the relevant supplied evidence IDs; the engineer needs a compact explanation they can paste into the incident record.
''', [
    "R1 selects client timer/header 6000 ms from the call option; server budget is capped at 5000 ms.",
    "R2 ignores legacy timeout:1, selects constructor timeoutMs 2500, sends 2500, and receives a 2500 ms server budget.",
    "R3 rejects Number('2s') as invalid before networking; it does not silently fall back to a default or the server's absent-header budget.",
    "The deployed 2.3.1 implementation and applicable 2.x migration note govern parsing and precedence; 1.8 seconds and 3.x duration-string support do not apply.",
    "5030 ms end-to-end receipt does not contradict a 5000 ms server computation budget or 6000 ms client timer because the clock intervals differ and network/response time is additional.",
    "A concrete valid two-second setting uses timeoutMs:2000 at the appropriate winning scope or numeric string 2000 in the environment when no higher-precedence setting overrides it.",
    "Cite source IDs near the main version, selection, and budget claims.",
    "Stay within the 350-word response limit while covering the three requests and source-scope distinction."
], ["Do not treat newest publication date as deployed-version authority.", "Do not parse 2s under the 3.x rule for the deployed 2.3.1 client."],
["Applies timeout seconds from 1.x to R2.", "Sends R3 or falls back silently after invalid parsing.", "Claims R1's 5030 ms response necessarily violates the server cap."],
constraints={"max_words":350}, source_ids=["A15-OLD", "A15-MIGRATION", "A15-IMPLEMENTATION", "A15-SERVER", "A15-LATEST", "A15-REQUESTS"], complexity_features=["five scoped sources", "configuration precedence", "versioned parsing", "different clock intervals", "compact sourced synthesis"],
source_expectations=["Use A15-IMPLEMENTATION and A15-MIGRATION for client behavior, A15-SERVER for server behavior, and explicitly scope out A15-OLD/A15-LATEST."], verification=["Executed a literal resolver simulation for all three requests and server-cap calculation."])

SOURCES["A03-API"] = {
    "url":"https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/List.html",
    "publisher":"Oracle Java SE 21 API specification",
    "consulted":"2026-11-16",
    "paraphrase":"Unmodifiable lists may contain mutable elements. Structural changes to a backing list outside its subList invalidate the specified semantics of that view.",
    "used_for":["A03"],
}
write_outputs()


a16_db=sqlite3.connect(":memory:")
a16_db.executescript("CREATE TABLE account(id INTEGER PRIMARY KEY,email TEXT NOT NULL,email_norm TEXT); INSERT INTO account VALUES(1,'Li@EX.test',NULL),(2,'li@ex.test',NULL),(3,'sam@ex.test',NULL); UPDATE account SET email_norm=lower(email);")
a16_collision=a16_db.execute("SELECT email_norm,COUNT(*) FROM account GROUP BY email_norm HAVING COUNT(*)>1").fetchall()
check("A16", "normalization collision", [list(x) for x in a16_collision], [["li@ex.test",2]])
a16_db.close()
a16_db=sqlite3.connect(":memory:")
a16_db.executescript("CREATE TABLE account(id INTEGER PRIMARY KEY,email TEXT NOT NULL,email_norm TEXT UNIQUE); INSERT INTO account VALUES(4,'PAT@EX.test',NULL),(5,'Pat@ex.test','pat@ex.test');")
check("A16", "mixed-writer shadow duplicate rows", a16_db.execute("SELECT COUNT(*) FROM account WHERE lower(email)='pat@ex.test'").fetchone()[0], 2)
a16_db.close()
add("A16", "database_migration_rolling_versions_and_identity_collisions", '''
This is an original synthetic rolling-deployment review. The service has account records with case-sensitive email identity, and the product team wants case-insensitive login. All addresses in this packet use ASCII characters, and normalization means applying lowercase to the entire string; we are not asking about real-world email standards or Unicode normalization. The migration must preserve account ownership and support a temporary mixed fleet of application versions.

[A16-OLD] Version 1 reads and writes account(id, email). email is non-null and unique under a case-sensitive comparison. Version 1 never references email_norm and inserts no value for it. It permits two different accounts whose emails differ only in letter case. Existing rows are (1, Li@EX.test), (2, li@ex.test), and (3, sam@ex.test). The accounts can have different owners and purchase histories. A rollback to version 1 must remain possible during the first deployment stage.

[A16-NEW] Version 2 can read email_norm and, when it is null, calculate lowercase(email) for a fallback lookup. On a successful account write, it writes both email and email_norm in one local transaction. Its proposed login behavior expects exactly one account for a normalized address. Its code does not implement an ownership-verification process for merging accounts. Version 2 does not stop version 1 instances from accepting new accounts.

[A16-DATABASE] The expansion migration adds nullable email_norm and later proposes a unique index on that column. In this synthetic database, the unique index permits multiple null values and rejects repeated non-null values. A backfill sets email_norm=lowercase(email) for existing rows. The backfill is resumable and may finish before the last version 1 instance is retired. There are no normalization triggers, no cross-column unique expression indexes, and no automatic database rule that populates a missing email_norm.

[A16-PLAN] The deployment checklist currently says: add the column; backfill; create the unique index; deploy version 2 to half the fleet; mark email_norm NOT NULL; rename email_norm to email and drop the original column; then deploy the remaining instances. The author says old binaries will keep working because the database still has a column named email at the end. They also believe a completed backfill permanently proves every future row will be normalized.

[A16-RACE] Consider a later stage in which existing identity collisions have already been resolved legitimately and the nullable unique index exists. An old instance inserts id 4 with email PAT@EX.test and null email_norm. A new instance then inserts id 5 with email Pat@ex.test and email_norm pat@ex.test. Both rows satisfy the described index. No ownership information permits us to conclude that these two accounts belong to the same person.

Explain which steps fail immediately on the initial data and which later steps are incompatible with the mixed fleet or rollback requirement. Work through the race and explain why fallback reads and a nullable unique index do not enforce normalized identity globally. Propose a staged expansion, reconciliation, writer transition, verification, and eventual contraction plan. Identify what must be decided by the product's account-ownership policy rather than by a convenient SQL deletion. Also state what evidence would justify enforcing NOT NULL and removing the old representation, and distinguish preserving old-column syntax from preserving the behavior an old binary relies on.
''', [
    "Initial lowercasing makes ids 1 and 2 both li@ex.test, so a unique normalized index cannot be created successfully without resolving the collision.",
    "Collision resolution is an account-ownership/business-policy issue; silently deleting or merging accounts is not justified.",
    "Old writers continue to create null email_norm values after a completed backfill, so the backfill alone is not a lasting invariant.",
    "The specified race admits ids 4 and 5, both normalized to pat@ex.test by fallback logic, because null uniqueness does not enforce the desired cross-representation identity.",
    "Enforcing NOT NULL while old inserts omit the field breaks version 1, and renaming/reusing a column name does not guarantee old semantics or safe rollback.",
    "A staged solution preserves both representations while readers/writers transition, addresses ongoing old writes using a compatible enforcement mechanism or complete writer retirement, and performs catch-up reconciliation.",
    "Enforce normalized uniqueness and required population only once collisions and all writer paths are controlled and verified; an equivalent database normalization enforcement mechanism may be proposed explicitly.",
    "Contract the old representation only after old binaries, recovery jobs, and the rollback window no longer require it, with checks for nulls, collisions, and consistency."
], ["Do not assume null values are rejected by the supplied unique index.", "Do not equate equal normalized addresses with proven shared ownership."],
["Endorses the checklist unchanged as compatible with the mixed fleet.", "Claims backfill plus nullable uniqueness prevents the shown race.", "Silently merges the initial two accounts."],
source_ids=["A16-OLD", "A16-NEW", "A16-DATABASE", "A16-PLAN", "A16-RACE"], complexity_features=["schema versus application compatibility", "normalization collisions", "concurrent writer versions", "rollback contract", "data-policy boundary"],
source_expectations=["Use the supplied index/null rules and version contracts rather than assuming a database trigger exists."], verification=["Executed SQLite collision detection and the nullable-index race under the supplied semantics."])


a17_code=r'''
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
'''
a17_out=execute("A17","python",a17_code)
check("A17","all snapshots",a17_out,"S1 [2, 2] [10, 2] [1, 2]\nS2 [99, 99] [10, 99] [1, 2]\nrows [{'n': 10}, {'n': 20}]\nbuckets [['x', 'y'], ['x', 'y']]\nouter-copy [['x', 'y'], ['x', 'y']]")
add("A17", "python_closures_binding_identity_and_shallow_copies", f'''
This is an original synthetic Python debugging exercise. A UI adapter builds callbacks while reading rows and later invokes them after the backing data has changed. A different part of the same adapter creates per-row buffers. The team has proposed “use defaults” and “make a copy” as universal repairs, but we need to understand exactly which references those operations preserve. There are no asynchronous tasks or threads in this example; every mutation happens in the displayed order.

[A17-CODE]

{fence(a17_code,"python")}

[A17-INTENT] There are two legitimate products the library might offer. A historical report callback should return the number that existed when the callback was constructed. A live object callback should follow later edits to the particular row object it was given, even if the source list later replaces that object with a new row. A third possible interface would instead follow whichever object currently occupies a source-list position. Those are distinct contracts, and the library has not yet selected one. Each row buffer, in contrast, is definitely required to be independent: appending a message for one row must not append it for another row.

[A17-REVIEW] One reviewer predicts that all three callback lists return 20 for the second row after replacement, because “a row is whatever is in that slot now.” Another thinks the default argument in objects takes a deep snapshot of the dictionary. A third believes the loop variable inside a list comprehension is recreated in a fresh independent closure for every lambda, so late must behave like objects. Finally, the buffer author believes buckets.copy creates independent inner lists, since the outer identity changes.

Please give the exact outputs at S1 and S2, the final rows display, and the contents of both buffer lists. Explain which values are evaluated when the callbacks are built and which lookups occur when they are invoked. I need a reference-based explanation that accounts for saved_second changing an object no longer present in rows, rather than a vague rule that closures “remember the loop.” In particular, explain why replacing a list element and mutating the previously referenced dictionary have different effects.

Assess each review claim and map the three existing callback constructions to the contracts they do or do not satisfy for this example. Explain why capturing an immutable integer now has a different consequence from capturing a mutable dictionary now, and why even that observation is not a universal deep-copy recipe for arbitrary nested values. Also explain the two independent aliasing steps in the buffer example: repeated references created by list multiplication and retained references created by a shallow outer copy.

Do not rewrite the program or provide replacement code. Describe the implementation choices in prose, including how an interface that intentionally follows a source-list index would differ conceptually and what independent buffer creation would need to accomplish. The purpose of this review is to choose the right behavior before changing code, so do not assume that one callback policy is always correct merely because it is easy to express.
''', [
    "S1 is late [2,2], objects [10,2], values [1,2].",
    "S2 is late [99,99], objects [10,99], values [1,2], while rows is [{'n':10},{'n':20}].",
    "Each lambda in late uses the same comprehension binding cell for row, which ends pointing to the original second dictionary; replacing the list slot does not rebind that cell.",
    "objects stores each dictionary reference in a default at construction, so later dictionary mutation remains visible; it does not deep-copy the dictionary.",
    "values evaluates and captures each integer at construction, meeting the historical-number contract for these immutable values.",
    "None of the shown constructions generally follows the current object at a list position; that contract needs an explicit later lookup using the container and an index.",
    "Both buckets and outer_copy display [['x','y'],['x','y']]; multiplication initially repeats one inner-list reference, and copying the outer list retains those same inner references.",
    "Describe independent buffer creation and contract-specific capture choices in prose without providing replacement code."
], ["Do not equate captured references with deep snapshots.", "Do not silently change the no-code-change request."],
["Predicts that replacing rows[1] changes all callbacks to 20.", "Claims list-comprehension iterations give the late lambdas distinct captured row cells.", "Claims shallow copying separates the inner buffers."],
constraints={"no_code_change":True}, source_ids=["A17-CODE","A17-INTENT","A17-REVIEW"], complexity_features=["binding cells versus objects", "replacement versus mutation", "three possible contracts", "two-level aliasing"],
source_expectations=["Use the exact order in A17-CODE; the intentional contract alternatives in A17-INTENT should not be collapsed into one."], verification=["Executed both callback snapshots and the nested-list aliasing example."])


a18_code=r'''
let reads = 0;
const secret = Symbol("secret");
const source = Object.create({ inherited: 9 });
Object.defineProperty(source, "hidden", { value: 7, enumerable: false });
source.meta = { tag: "old" };
source.created = new Date("2025-01-01T00:00:00.000Z");
source.optional = undefined;
Object.defineProperty(source, "amount", {
  enumerable: true,
  get() { reads += 1; return reads; }
});
source[secret] = "token";
const spread = { ...source };
const json = JSON.parse(JSON.stringify(source));
const cloned = structuredClone(source);
source.meta.tag = "new";
source.created.setUTCFullYear(2030);
for (const [name, value] of Object.entries({spread, json, cloned})) {
  console.log(name, JSON.stringify({
    tag: value.meta.tag,
    dateType: value.created instanceof Date ? "Date" : typeof value.created,
    year: value.created instanceof Date ? value.created.getUTCFullYear() : value.created,
    optionalOwn: Object.hasOwn(value, "optional"),
    amount: value.amount,
    hiddenOwn: Object.hasOwn(value, "hidden"),
    inheritedOwn: Object.hasOwn(value, "inherited"),
    secretOwn: Object.hasOwn(value, secret),
    amountGetter: typeof Object.getOwnPropertyDescriptor(value, "amount").get
  }));
}
console.log("reads", reads);
try { structuredClone({ run() {} }); }
catch (error) { console.log("function-clone", error.name); }
'''
a18_out=execute("A18","javascript",a18_code)
a18_rows={line.split(" ",1)[0]:json.loads(line.split(" ",1)[1]) for line in a18_out.splitlines()[:3]}
check("A18","spread result",a18_rows["spread"],{"tag":"new","dateType":"Date","year":2030,"optionalOwn":True,"amount":1,"hiddenOwn":False,"inheritedOwn":False,"secretOwn":True,"amountGetter":"undefined"})
check("A18","json result",a18_rows["json"],{"tag":"old","dateType":"string","year":"2025-01-01T00:00:00.000Z","optionalOwn":False,"amount":2,"hiddenOwn":False,"inheritedOwn":False,"secretOwn":False,"amountGetter":"undefined"})
check("A18","structured clone result",a18_rows["cloned"],{"tag":"old","dateType":"Date","year":2025,"optionalOwn":True,"amount":3,"hiddenOwn":False,"inheritedOwn":False,"secretOwn":False,"amountGetter":"undefined"})
check("A18","function error",a18_out.splitlines()[-1],"function-clone DataCloneError")
add("A18", "javascript_copying_serialization_and_accessors", f'''
This is an original synthetic JavaScript data-contract review. A team wants to replace three different copying techniques with a single helper called snapshot. Their tests compare the printed JSON and miss differences in types, omitted properties, and observable getter behavior. The following self-contained program runs in a modern Node environment that provides structuredClone. No proxy objects, custom toJSON method, external mutation, or host DOM values are involved.

[A18-CODE]

{fence(a18_code,"javascript")}

[A18-CONTRACT] The intended report must be independent of later edits to meta and created. Its consumers call Date methods on created. They distinguish a property that is present with value undefined from a property that is absent. A symbol-keyed internal marker is currently used by one consumer, but the product owner is willing to remove that requirement if the change is explicitly documented. No consumer should depend on reading the report repeatedly to increment a hidden counter. A future plugin might attach a function, so the helper's unsupported-value behavior also needs a declared policy.

[A18-CLAIMS] The first reviewer says spreading an object is a deep copy because it creates a new outer object. The second says a JSON round trip preserves every value that JavaScript can represent. The third says structuredClone preserves every original property descriptor and never runs user code because it is a built-in. All three reviewers agree that equal-looking printed output is sufficient proof of interchangeable API behavior. The local fixture is intended to test those beliefs, not to make a universal statement that one copying technique is always best.

Explain the result for each copy: which meta tag it sees after the mutations, the type and content of created, whether optional and the symbol-keyed property remain own properties, and what happens to inherited and nonenumerable properties. Account for the different amount values and total getter reads. Distinguish evaluating a getter during copying from preserving that getter as a descriptor on the result; those two behaviors have very different implications for a snapshot.

Then assess which technique most nearly meets the current report contract and what explicit transformation or policy would still be needed. Explain the function-clone experiment and why choosing a failure policy matters when a plugin changes the input shape. A suggestion may involve constructing a deliberate data-transfer representation rather than promising a general deep clone of arbitrary JavaScript objects. Please keep the distinction between the exact demonstrated types and broader unsupported object categories clear, and do not treat loss of the internal marker as acceptable until it has been made an intentional contract change.
''', [
    "Spread shares meta and Date references, so it sees tag new and a Date in year 2030; JSON and structured clone retain tag old.",
    "JSON converts created to the original ISO string, whereas structured clone retains an independent Date in year 2025.",
    "Spread and structured clone preserve the own optional property with undefined; the JSON round trip omits it.",
    "The symbol-keyed property survives spread but not the shown JSON or structured clone; inherited and nonenumerable properties do not become own properties in these results.",
    "The three copies invoke the amount getter in order and capture values 1,2,3, with total reads 3; all result descriptors hold values rather than the original getter.",
    "Creating a fresh outer object does not itself separate nested references, and serialization is not a type-preserving clone of all JavaScript values.",
    "structuredClone of a function-bearing object throws DataCloneError in the shown experiment; a declared reject/transform/omit policy is needed for future plugin values.",
    "structuredClone most nearly meets the independent nested data, Date, and explicit-undefined requirements here, but the symbol marker requires an explicit separately handled or intentionally removed contract requirement; constructing a deliberate report shape is also valid."
], ["Do not call JSON output equivalence proof of equivalent object behavior.", "Do not claim structuredClone universally preserves descriptors or supports functions."],
["Says spread isolates nested mutation.", "Says JSON preserves Date objects or own undefined values.", "Claims the getter is retained unevaluated on the clone."],
source_ids=["A18-CODE","A18-CONTRACT","A18-CLAIMS"], complexity_features=["three copy mechanisms", "getter side effects", "property-key categories", "type preservation", "future unsupported values"],
source_expectations=["Ground exact observations in A18-CODE and evaluate suitability against the explicit contract rather than a generic cloning slogan."], verification=["Executed Node fixture and asserted all copied properties, types, accessor results, and function-clone failure."])


a19_code=r'''
import java.lang.management.ManagementFactory;
import java.util.concurrent.CountDownLatch;

class A19_fixture {
    static final Object left = new Object();
    static final Object right = new Object();
    static final CountDownLatch holdingFirst = new CountDownLatch(2);
    static void transfer(Object first, Object second) {
        synchronized (first) {
            holdingFirst.countDown();
            try { holdingFirst.await(); }
            catch (InterruptedException e) { throw new RuntimeException(e); }
            synchronized (second) {
                System.out.println("transfer-completed");
            }
        }
    }
    public static void main(String[] args) throws Exception {
        Thread a = new Thread(() -> transfer(left, right), "A");
        Thread b = new Thread(() -> transfer(right, left), "B");
        a.setDaemon(true);
        b.setDaemon(true);
        a.start(); b.start();
        holdingFirst.await();
        for (int i = 0; i < 2000; i++) {
            if (a.getState() == Thread.State.BLOCKED && b.getState() == Thread.State.BLOCKED)
                break;
            Thread.sleep(1);
        }
        long[] deadlocked = ManagementFactory.getThreadMXBean().findMonitorDeadlockedThreads();
        System.out.println("states=" + a.getState() + "," + b.getState());
        System.out.println("deadlocked=" + (deadlocked == null ? 0 : deadlocked.length));
    }
}
'''
a19_out=execute("A19","java",a19_code)
check("A19","deadlock fixture observation",a19_out,"states=BLOCKED,BLOCKED\ndeadlocked=2")
a19_repair_code = a19_code.replace("transfer(right, left)", "transfer(left, right)")
a19_repair_code = a19_repair_code.replace("        holdingFirst.await();\n        for", "        for")
a19_repair_code = a19_repair_code.replace(
    "a.getState() == Thread.State.BLOCKED && b.getState() == Thread.State.BLOCKED",
    "(a.getState() == Thread.State.BLOCKED && b.getState() == Thread.State.WAITING) || (b.getState() == Thread.State.BLOCKED && a.getState() == Thread.State.WAITING)")
a19_repair_code = a19_repair_code.replace(
    'System.out.println("states=" + a.getState() + "," + b.getState());',
    'String[] states = {a.getState().toString(), b.getState().toString()}; java.util.Arrays.sort(states); System.out.println("states=" + String.join(",", states));')
a19_repair_out=execute("A19_repair","java",a19_repair_code)
VERIFICATIONS["A19"]["same_order_repair_execution"] = VERIFICATIONS.pop("A19_repair")
check("A19","same-order repair retains latch deadlock",a19_repair_out,"states=BLOCKED,WAITING\ndeadlocked=0")
add("A19", "java_monitor_deadlock_and_misleading_repair", f'''
This is an original synthetic Java concurrency investigation. The real service transfers inventory between two objects. The reduced program below contains no inventory arithmetic because we first need to understand why neither transfer reaches its critical operation. The latch is test instrumentation intended to force a particular schedule. It is not part of the production business requirement. Both worker threads are daemon threads only so that this demonstrator can exit after reporting the deadlock.

[A19-CODE]

{fence(a19_code,"java")}

[A19-OBSERVATION] On the supplied OpenJDK 21 run, no transfer-completed line appears. The final diagnostic is states=BLOCKED,BLOCKED and deadlocked=2. Both workers had reached holdingFirst.countDown, so the latch initially reaches zero. The monitoring thread's timeouts and daemon flags are not intended to release either object's monitor; they just bound how long the demonstration stays alive.

[A19-REVIEW] One engineer says synchronized methods cannot deadlock because Java automatically releases a monitor. Another recommends making both calls transfer(left,right), leaving the latch exactly where it is. A third recommends calling interrupt on both workers because an interrupt should make synchronized acquisition fail immediately and release every lock. Someone else says changing the field declarations to volatile would solve the problem by ensuring both threads see the latest lock references. We need to distinguish a correct principle about lock ordering from whether the proposed literal edit fixes this particular test harness.

[A19-REQUIREMENT] In production, a transfer must check and update two inventory objects atomically with respect to other transfers touching either object. No unrelated network request or callback needs to execute while both monitors are held. The two objects have stable unique identifiers, and the same-object transfer can be handled explicitly. A correct design should permit opposite-direction transfers without cyclic waiting. The regression test should create concurrency without forcing one thread to wait for a participant that cannot enter its required critical section.

Explain the wait-for cycle in the observed run and why automatic monitor release on exiting a block does not guarantee that a blocked thread will reach the exit. Then work through the proposed same-order edit with the latch unchanged: which worker can count down, which monitor it holds while awaiting the other worker, and why the diagnostic may differ from a pure monitor-to-monitor cycle. Do not call that edit a complete fix without considering the instrumentation.

Recommend a production locking approach and a corresponding corrected test arrangement. Explain the roles of a total lock order, stable object identity, and handling a transfer to the same object. Assess interrupt and volatile as proposed repairs without overclaiming what either mechanism does. Finally, distinguish deadlock prevention from fairness or guaranteed progress under arbitrary scheduling; the team wants a precise explanation of the property it is improving, not a promise that every transfer always finishes within a fixed deadline.
''', [
    "In the observed run A holds left and waits for right, while B holds right and waits for left; the latch has already reached zero.",
    "Automatic monitor release happens on leaving the synchronized block, but these workers cannot reach that exit while stuck acquiring the other monitor.",
    "Changing both calls to left then right while keeping the latch inside the first lock creates another deadlock: the first worker holds left awaiting the second countdown, while the second cannot acquire left to count down.",
    "That revised dependency includes a latch wait, so a monitor-only cycle detector need not report the same two-monitor deadlock even though progress is blocked.",
    "A production fix can impose a consistent total acquisition order by stable unique object identifiers and keep the atomic two-object operation inside those locks.",
    "The test barrier/latch should be moved before acquisition or otherwise redesigned so it does not wait for a thread prevented from reaching it by a held lock; handle the same-object case explicitly or rely correctly on monitor reentrancy.",
    "Thread.interrupt is not a general forced-release or interruptible intrinsic-monitor-entry mechanism; volatile changes visibility rather than eliminating the lock-order cycle.",
    "Deadlock prevention does not by itself provide fairness, bounded waiting, or a deadline guarantee."
], ["Do not assume every deadlock is discoverable as an intrinsic-monitor cycle.", "Do not propose forcibly stopping threads as a safe inventory transaction mechanism."],
["Claims synchronized cannot deadlock.", "Endorses the literal same-order edit with the unchanged latch as a complete fix.", "Claims volatile or interrupt automatically releases owned monitors."],
source_ids=["A19-CODE","A19-OBSERVATION","A19-REVIEW","A19-REQUIREMENT"], complexity_features=["forced interleaving", "monitor cycle", "repair-induced latch cycle", "lock-order invariant", "safety versus fairness"],
source_expectations=["Separate A19-OBSERVATION from the analysis of the proposed edit, and distinguish production rules from test instrumentation."], verification=["Executed Java monitor deadlock demonstration; independently checked the same-order edit's dependency cycle from its explicit lock/latch states."])


a20_schema=r'''
CREATE TABLE event(id INTEGER PRIMARY KEY, account TEXT, ts INTEGER, status TEXT, delta INTEGER);
INSERT INTO event VALUES(1,'A',10,'open',5),(2,'A',20,'review',7),(3,'A',20,'paid',-2),(4,'A',30,'closed',-1);
'''
a20_query=r'''
SELECT id,ts,status,
       SUM(delta) OVER (PARTITION BY account ORDER BY ts) AS running_total,
       LAST_VALUE(status) OVER (PARTITION BY account ORDER BY ts) AS final_status
FROM event
ORDER BY ts,id;
'''
a20_observed=sql_check("A20",a20_schema,a20_query)
check("A20","default peer-sensitive sums",[r[3] for r in a20_observed],[5,10,10,9])
a20_fixed=r'''
SELECT id,
 SUM(delta) OVER (PARTITION BY account ORDER BY ts,id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW),
 LAST_VALUE(status) OVER (PARTITION BY account ORDER BY ts,id ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING)
FROM event WHERE ts <= 20 ORDER BY ts,id;
'''
check("A20","explicit frame in selected population",sql_check("A20",a20_schema,a20_fixed),[[1,5,"paid"],[2,12,"paid"],[3,10,"paid"]])
add("A20", "sql_window_frames_peer_order_and_filter_scope", f'''
This is an original synthetic SQL reporting problem. The query runs on SQLite with its standard window-function behavior. A ledger report has three different notions of “last”: the status on the current event, the last status among timestamp peers, and the final status in the selected reporting population. The current implementation has given those notions the same column name, which makes a small test result look more convincing than it is.

[A20-DATA]

{fence(a20_schema,"sql")}

[A20-QUERY]

{fence(a20_query,"sql")}

[A20-FRAMES] For this exercise, an ordered aggregate or LAST_VALUE window without an explicit frame uses RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW. In such a RANGE frame, rows tied on the window's ORDER BY value are peers and the current frame includes the whole current peer group. An outer ORDER BY controls presentation and does not add an omitted tie-breaker to a window's own ORDER BY. These are supplied semantics so we can focus on reasoning about the query rather than guessing a database dialect.

[A20-CONTRACT] The intended running balance applies events one at a time in ascending (ts,id) order. The final_status column is supposed to display, on every returned row, the status of the last event within the selected account and reporting population, also using (ts,id) order. For the example report, the population includes only ts<=20. A later event at ts=30 is not allowed to affect either the displayed running balances or the displayed final status. The tie-break by id is an explicit business rule, not an inference from insertion order.

[A20-OBSERVATION] In one local run of the unfiltered current query, running_total was 5,10,10,9 for ids 1 through 4, and the two timestamp-20 rows displayed paid as final_status. The developer expected running totals 5,12,10,9 and closed as the status on all four rows. They propose adding id only to the outer ORDER BY, then wrapping the entire query in an outer SELECT with WHERE ts<=20. Another proposal removes window ordering completely to get a whole-partition sum, calling that equivalent to a running balance.

Explain the observed running totals and the role of the peer group. Say which aspect of the paid observation depends on the unspecified order between tied statuses and which summed result is invariant to that tie order. Explain why LAST_VALUE does not mean “last in the entire partition” with the current frame. Then show a corrected query or precise window definitions for the intended ts<=20 report and give its running balances and repeated final status.

We also need to understand why applying the time filter before versus after window evaluation can change the answer, even if the same event rows are eventually displayed. Compare the proposed outer filter with the contract, and evaluate both other proposed repairs. Please keep the window's logical ordering, its frame, the selected population, and the final presentation order separate; a correct explanation should locate each error rather than prescribe one large SQL expression without explaining its parts.
''', [
    "Default RANGE frames include both ts=20 peers, producing running sums 5,10,10,9 rather than event-by-event 5,12,10,9.",
    "LAST_VALUE sees the end of the current frame, not automatically the end of the partition.",
    "The timestamp-20 total is invariant to peer order, but choosing paid versus review as a last peer status is not guaranteed without a window tie-breaker.",
    "Adding id only to the outer presentation ordering does not fix the order used inside the window.",
    "Use window ORDER BY ts,id with an explicit ROWS cumulative frame for the running total, and a whole-selected-partition frame ending UNBOUNDED FOLLOWING for final status.",
    "Apply ts<=20 to the input relation before these windows to satisfy the selected-population contract; output rows have balances 5,12,10 and final status paid on each.",
    "Computing whole-partition final status before an outer filter can include closed at ts=30 despite displaying only earlier rows.",
    "Removing ordering produces a partition total rather than the required running balance; ordering, frame, filtering scope, and display order solve different problems."
], ["Do not treat incidental insertion order as the explicit tie-break rule.", "Do not claim the same final rows imply the same window inputs."],
["Claims outer ORDER BY alone makes window ties deterministic.", "Uses the future closed status for the requested cutoff report.", "Calls a full-partition total a running balance."],
source_ids=["A20-DATA","A20-QUERY","A20-FRAMES","A20-CONTRACT","A20-OBSERVATION"], complexity_features=["RANGE peers versus ROWS", "two ordering scopes", "window input population", "observed versus guaranteed tie order"],
source_expectations=["Use the supplied frame semantics and explicitly distinguish A20-OBSERVATION from the deterministic business order in A20-CONTRACT."], verification=["Executed faulty peer-frame query and corrected cutoff report in SQLite."])
write_outputs()


a21_code=r'''
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN

cent = Decimal("0.01")
raw = [Decimal("0.335"), Decimal("0.335"), Decimal("0.335")]
print("line-rounded", sum(x.quantize(cent, rounding=ROUND_HALF_UP) for x in raw))
print("invoice-rounded", sum(raw).quantize(cent, rounding=ROUND_HALF_UP))
print("float-constructor", Decimal(1.005).quantize(cent, rounding=ROUND_HALF_UP))
print("text-constructor", Decimal("1.005").quantize(cent, rounding=ROUND_HALF_UP))
print("half-up", Decimal("0.325").quantize(cent, rounding=ROUND_HALF_UP))
print("half-even", Decimal("0.325").quantize(cent, rounding=ROUND_HALF_EVEN))
print("binary-round", round(2.675, 2))
'''
a21_out=execute("A21","python",a21_code)
check("A21","rounding outputs",a21_out,"line-rounded 1.02\ninvoice-rounded 1.01\nfloat-constructor 1.00\ntext-constructor 1.01\nhalf-up 0.33\nhalf-even 0.32\nbinary-round 2.67")
a21_floor=[33,33,33]
for i in range(101-sum(a21_floor)): a21_floor[i]+=1
check("A21","largest-remainder allocation",a21_floor,[34,34,33])
add("A21", "python_decimal_representation_rounding_and_allocation", f'''
This is an original synthetic invoice-calculation exercise. We are not asking about legal accounting rules: the policy below is an invented product contract and is authoritative for the task. Our team has discovered a one-cent disagreement between a receipt total, stored line totals, and a refund calculation. A developer says using Decimal will solve every disagreement automatically, while another says a tiny binary error cannot matter because all displayed values have only two decimal places.

[A21-POLICY] Inputs arrive as exact decimal text in units of currency. Calculate each raw line amount exactly, add the raw amounts, and round the invoice total once to cents using round-half-up. Then allocate that rounded invoice total to line items so that the stored integer-cent line amounts sum exactly to the invoice total. For allocation, take the floor of each raw line amount in cents, distribute the remaining cents to the largest fractional remainders, and break equal remainders by ascending line identifier. This example contains only positive amounts. A refund of a whole line must use its originally stored allocated cents.

[A21-INVOICE] Line identifiers 10, 20, and 30 each have raw amount 0.335. There are no taxes, discounts, foreign-exchange conversions, or further lines. A previous implementation independently rounded each line to two decimal places and added those rounded amounts. A draft repair rounds only the invoice total but still computes every later refund independently from the raw line amount. The receipt must remain reconcilable after any sequence of whole-line refunds.

[A21-CODE] The team ran these experiments on Python 3.12:

{fence(a21_code,"python")}

[A21-REVIEW] One review says Decimal(1.005) and Decimal("1.005") must be equivalent because the source text looks identical after the quotes are removed. Another says Python's round output proves that ties are always rounded downward. A third says half-even and half-up are interchangeable whenever the output has two decimal places. The final reviewer suggests storing three equal 34-cent lines and “fixing the extra cent in the display,” although line refunds and reconciliation use stored values, not the display string.

Please explain every printed result that is relevant to these disagreements and distinguish the decimal policy from the representation of a binary floating-point input. Calculate the required invoice total and the three stored line amounts under the allocation rule. Explain why the old per-line rounding policy disagrees with the new invoice-level policy even if every operation uses exact decimal arithmetic, and why both policies cannot be implemented simultaneously for this particular invoice.

Then evaluate the refund repair and the display-only repair. Explain how to make whole-line refunds reconcile with the original charge without inventing a new cent each time a line is refunded. We need a concrete explanation of where rounding belongs, how ties are resolved, and what must be stored; do not respond only with “use a money library.” Also identify which details would need a new policy if negative amounts or partial-line refunds were later introduced, since the supplied allocation procedure only defines this positive whole-line case.
''', [
    "Exact per-line half-up rounding yields 0.34 each and total 1.02, whereas rounding the raw invoice total 1.005 once yields 1.01.",
    "Decimal constructed from binary float 1.005 preserves its already inexact value and rounds to 1.00 here; Decimal from the exact text rounds to 1.01.",
    "For 0.325, half-up gives 0.33 and half-even 0.32, so the rounding modes are materially different.",
    "round(2.675,2)=2.67 reflects the represented binary value and Python rounding behavior, not a general rule that exact decimal ties always round down.",
    "Raw line cents are 33.5 each; floor totals 99 cents, and the two remaining cents go to ids 10 and 20, yielding stored cents 34,34,33.",
    "Independent rounding and invoice-level rounding are different policies even with exact Decimal arithmetic; choosing representation alone does not choose rounding scope.",
    "Whole-line refunds must use stored allocated cents so all three refunds total the charged 101 cents; recomputing 34 for every raw line or display-only adjustment breaks reconciliation.",
    "Negative amounts and partial refunds require explicit extensions for allocation/tie handling and refund conservation rather than assuming the positive whole-line rule fully defines them."
], ["Do not make unsupplied claims about statutory invoice rules.", "Do not treat decimal text and a decimal created from float as identical exact inputs."],
["Reports the policy invoice total as 1.02.", "Stores three 34-cent lines while claiming stored totals reconcile to 101 cents.", "Endorses recalculating each whole-line refund as 34 cents."],
source_ids=["A21-POLICY","A21-INVOICE","A21-CODE","A21-REVIEW"], complexity_features=["representation versus policy", "rounding scope", "deterministic remainder allocation", "refund conservation"],
source_expectations=["Use the invented A21-POLICY as the policy authority; code results alone do not select a business rounding rule."], verification=["Executed Decimal and float examples, then verified the integer-cent remainder allocation."])


import heapq
a22_queue=[(0,"J1",1),(0,"J2",1),(0,"J3",1)]
heapq.heapify(a22_queue)
a22_outcomes={"J1":["fail","fail","success"],"J2":["fail","success"],"J3":["success"]}
a22_deadlines={"J1":6,"J2":10,"J3":None}
a22_now=0
a22_trace=[]
while a22_queue:
    due,job,attempt=heapq.heappop(a22_queue)
    a22_now=max(a22_now,due)
    deadline=a22_deadlines[job]
    if deadline is not None and a22_now+1>deadline:
        a22_trace.append([job,"expired",a22_now,attempt]); continue
    start=a22_now
    a22_now+=1
    outcome=a22_outcomes[job][attempt-1]
    a22_trace.append([job,outcome,start,a22_now,attempt])
    if outcome=="fail" and attempt<3:
        heapq.heappush(a22_queue,(a22_now+2**(attempt-1),job,attempt+1))
check("A22","complete execution schedule",a22_trace,[
    ["J1","fail",0,1,1],["J2","fail",1,2,1],["J3","success",2,3,1],
    ["J1","fail",3,4,2],["J2","success",4,5,2],["J1","expired",6,3]])
add("A22", "state_machine_retry_backoff_deadlines_and_queue_order", '''
This is an original synthetic queue-scheduler specification. A team is trying to explain why one job did not receive its last permitted attempt, even though the configured attempt limit was not exhausted. We need to distinguish elapsed time, queue order, backoff eligibility, and the number of attempts actually executed. No behavior of a particular queue product is implied; the rules below are complete for this exercise.

[A22-SCHEDULER] There is one worker. Each attempt takes exactly one second of worker time, including an attempt that fails. The worker never runs attempts concurrently and immediately selects the next eligible attempt when it becomes free. The priority queue is ordered by scheduled eligibility time, then lexical job identifier, then attempt number. A scheduled time is a lower bound on when work may start, not a reservation of the worker. If nothing is eligible, the worker advances to the earliest scheduled time. Enqueued retries do not jump ahead of older eligible jobs.

[A22-RETRY] Maximum attempts is three, including the initial attempt. After retryable failure of attempt n, schedule attempt n+1 at completion_time + 2^(n-1) seconds. Thus the first failure adds one second after that failure completes, the second adds two seconds, and no retry is scheduled after the third attempt. A success ends the job. Every failure specified in the input is retryable; permanent invalid-input failures in a real service would require a different policy. There is no random jitter in this exercise.

[A22-DEADLINE] Each job may have an absolute deadline. When an attempt is selected to start, first check whether its known completion time, start+1, would exceed that deadline. If so, expire the job immediately without executing that attempt. A completion exactly at the deadline is allowed. Do not expire a retry early when it is enqueued; the check happens only when it is selected. Deadlines do not change queue priority. The worker starts free at time zero.

[A22-INPUT] All initial attempts have scheduled eligibility time zero:

| Job | Absolute deadline | Outcomes if attempts are actually executed |
|---|---:|---|
| J1 | 6 | failure, failure, success |
| J2 | 10 | failure, success |
| J3 | none | success |

[A22-CLAIMS] The incident report says exponential backoff schedules J1 at absolute times 1 and 2, because it measures every delay from the original enqueue. It says J1's first retry must run before J3 because retrying an old job is inherently higher priority. Finally, it says the third listed outcome proves J1 eventually succeeds: the maximum-attempt setting “guarantees three tries.” One proposed repair removes the deadline check to make the graph show a success, without discussing why the deadline exists.

Please reconstruct the actual worker timeline, including every start, completion, retry eligibility time, and idle interval. Identify which outcomes in the input are realized and which remain hypothetical because an attempt never starts. Explain the distinct roles of maximum attempts and an absolute deadline, and evaluate all three incident claims. Then discuss a sensible production policy for an expired job and what instrumentation would distinguish queue waiting from retry delay and execution time. If you mention jitter, explain which cross-worker synchronization problem it could address and why it does not change the deterministic answer requested here.
''', [
    "J1 attempt 1 runs 0–1 and fails, scheduling its retry for time 2; J2 attempt 1 runs 1–2 and fails, scheduling its retry for time 3.",
    "J3's original due time zero keeps it ahead of retries, so it succeeds during 2–3.",
    "J1 attempt 2 runs 3–4, fails, and schedules attempt 3 for time 6; J2 attempt 2 runs 4–5 and succeeds.",
    "The worker is idle from 5 to 6; at 6 J1's hypothetical completion would be 7, beyond deadline 6, so it expires without a third executed attempt.",
    "J1's listed third success is a counterfactual outcome conditional on execution and does not override the deadline; maximum attempts is an upper bound including the initial attempt.",
    "Backoff is measured from actual failure completion, and due times establish eligibility rather than guaranteed start times or retry priority.",
    "A reasonable expiry policy records an explicit terminal/needs-review outcome or permitted recovery decision rather than silently removing the deadline to manufacture success.",
    "Instrumentation should separate due/enqueue, start, completion, attempt count, and expiry reason; jitter addresses correlated retries across workers but is absent from this fixture."
], ["Do not schedule delays from original enqueue contrary to A22-RETRY.", "Do not count an expired selection as an executed attempt."],
["Claims J1 completes successfully at 7 under the stated deadline.", "Runs J1 retry before J3 at time 2.", "Treats max attempts as a minimum number guaranteed to execute."],
source_ids=["A22-SCHEDULER","A22-RETRY","A22-DEADLINE","A22-INPUT","A22-CLAIMS"], complexity_features=["priority queue simulation", "completion-relative backoff", "absolute deadlines", "hypothetical outcomes", "observability design"],
source_expectations=["Use the exact supplied scheduling and deadline boundary rules, not generic retry defaults."], verification=["Executed a heap-based scheduler and asserted the complete timeline including expiry."])


a23_north_pre=statistics.mean([84,88]);a23_north_post=statistics.mean([100,104])
a23_south_pre=statistics.mean([51,52]);a23_south_post=statistics.mean([55,56])
check("A23","difference in differences",(a23_north_post-a23_north_pre)-(a23_south_post-a23_south_pre),12)
check("A23","pretrend weekly differential",(88-80)/2-(52-50)/2,3)
check("A23","descriptive trend extrapolation adjustment",12-3*2,6)
add("A23", "causal_inference_difference_in_differences_and_trend_assumptions", '''
This is an original synthetic operations-policy evaluation. Two regional support centers report the percentage of tickets resolved within two days. North adopted a new routing tool at week zero; South did not. The team wants to describe the tool's causal impact, but the historical series and a simultaneous staffing change make the usual comparison difficult. Percentages in this packet are exact descriptive summaries of the observed tickets, not estimates with supplied standard errors.

[A23-SERIES]

| Week relative to rollout | North, tool introduced at 0 | South, no tool |
|---:|---:|---:|
| -3 | 80 | 50 |
| -2 | 84 | 51 |
| -1 | 88 | 52 |
| 0 | 100 | 55 |
| 1 | 104 | 56 |

[A23-ANALYSIS] The prespecified descriptive before period is weeks -2 and -1, equally weighted; the after period is weeks 0 and 1, equally weighted. The proposed difference-in-differences estimate is North's after-minus-before change minus South's after-minus-before change. Outcomes use the same resolution definition throughout. Ticket counts, individual identifiers, and sampling variances are not included, so do not invent a standard error or a significance level from these five rows alone.

[A23-CONTEXT] North was already improving faster before rollout. At week zero it also received five experienced temporary staff; South received none. Staff assignment and tool adoption were both management decisions, not randomized. North and South serve somewhat different customer groups, and the possibility of changing case mix has not been investigated. There is no claim that the two regions' outcome levels needed to be identical for a valid design; the concern is the unobserved comparison trend that would have occurred without the tool.

[A23-CLAIMS] The presentation says: “North improved by sixteen points, so the tool's effect is sixteen points. Subtracting South's four-point improvement proves the tool's effect is twelve points. A preliminary pretrend test was not statistically significant, which proves the parallel-trends assumption. If we subtract the prior three-point weekly trend difference as well, the remaining six points must be the true effect.” The preliminary test's model, uncertainty, and sample size were not retained. The table alone does not resolve its statistical power.

[A23-DECISION] The organization needs to decide whether to expand the tool, expand staffing, or both. It can randomize future rollout timing across additional comparable centers and can measure staffing, case mix, and ticket-level outcomes. It cannot undo the already completed North rollout. The operational decision therefore concerns distinguishing the tool's contribution from the staffing package, not merely describing a positive post-rollout change.

Please compute the specified before and after averages and the descriptive difference-in-differences. Explain the counterfactual assumption needed to interpret that contrast causally and why equal baseline levels are not the essential requirement. Use the pre-period pattern to assess the presentation's reasoning without pretending a few data points establish the future untreated trend with certainty.

Also evaluate the six-point detrended calculation: show the arithmetic under a literal extrapolation of the observed pretrend, then explain why that extra modeling choice does not make the answer automatically causal. Address the simultaneous staffing change and the inconclusive pretrend test. Recommend a feasible follow-up design that could distinguish the tool-only effect from a combined tool-and-staffing effect, and state what can be responsibly reported from this packet right now.
''', [
    "Before averages are North 86 and South 51.5; after averages are North 102 and South 55.5.",
    "Observed changes are +16 and +4 percentage points, producing a descriptive difference-in-differences of +12 points.",
    "A causal interpretation needs an appropriate parallel counterfactual trend and no differential coincident cause/other identifying assumptions; equal starting outcome levels are not required.",
    "Pre-rollout North rises 4 points per week while South rises 1, suggesting a 3-point weekly trend difference that challenges a simple parallel-trends story.",
    "The midpoints of the specified before and after periods are two weeks apart; literal continuation of the pretrend differential would explain 6 of the 12 points, leaving a descriptive detrended contrast of 6.",
    "That six-point calculation depends on unverified trend extrapolation and does not remove the simultaneous differential staffing change or possible case-mix changes.",
    "Failure to reject a pretrend test does not prove parallel trends, especially without power/model details; no uncertainty interval can be recovered from the supplied percentages alone.",
    "Recommend additional randomized rollout/blocking or a design varying tool and staffing separately to distinguish tool-only from package effects; report observed contrasts with the identification limitations now."
], ["Do not require equal baseline levels as a condition for difference-in-differences.", "Do not fabricate a p-value or causal standard error."],
["Calls 12 or 6 points the proven causal effect.", "Says a nonsignificant pretrend test proves the counterfactual assumption.", "Ignores the simultaneous North-only staffing change."],
source_ids=["A23-SERIES","A23-ANALYSIS","A23-CONTEXT","A23-CLAIMS","A23-DECISION"], complexity_features=["descriptive versus causal contrast", "parallel counterfactual trends", "differential pretreatment trend", "simultaneous intervention", "follow-up design"],
source_expectations=["Tie causal qualifications to A23-CONTEXT and calculation weights to A23-ANALYSIS; do not treat an unreported test as conclusive evidence."], verification=["Executed period averages, difference-in-differences, and the explicitly conditional trend-extrapolation arithmetic."])


check("A24","single request optimized latency",8/4+12,14)
check("A24","single request speedup",20/14,10/7,1e-12)
check("A24","maximum speedup from CPU alone",20/12,5/3,1e-12)
check("A24","workload before mean ms",.9*10+.1*100,19)
check("A24","workload after mean ms",.9*8+.1*150,22.2,1e-12)
check("A24","mean latency relative increase",22.2/19-1,16/95,1e-12)
check("A24","average request speedup ratios",.9*(10/8)+.1*(100/150),143/120,1e-12)
check("A24","mean requests in system after",200*.0222,4.44,1e-12)
add("A24", "performance_units_weighted_ratios_bottlenecks_and_queueing", '''
This is an original synthetic performance review combining two separate experiments on the same service. The first is a controlled single-path microbenchmark; the second is a representative workload comparison with a fixed endpoint mix. They answer different questions and must not be silently treated as if every request follows the microbenchmark's timing. We need to decide what can honestly be claimed about the optimization.

[A24-MICRO] One isolated request path spends 8 milliseconds in a CPU stage followed by 12 milliseconds waiting for a database result. Those stages are serial for this path. The optimization makes the CPU stage exactly four times as fast and does not change the database stage. Ignore queueing, communication overlap, and measurement uncertainty for this microbenchmark. A vendor slide concludes that this proves a fourfold improvement in complete request latency and service throughput.

[A24-WORKLOAD] A separate replay contains exactly 900 fast-endpoint requests and 100 slow-endpoint requests before and after the change. Every fast request takes 10 milliseconds before and 8 milliseconds after. Every slow request takes 100 milliseconds before and 150 milliseconds after. These are complete response times including whatever waiting occurred in the replay. The endpoint counts stay fixed. There are no errors, cancellations, missing requests, or differences in payload mix within an endpoint. For the requested 95th percentile, sort the 1000 response times and use the 950th value.

[A24-DASHBOARD] The dashboard calculates a speedup for each request as old_time/new_time, averages those 1000 ratios, and labels the result “overall speedup.” It also averages the two endpoint mean latencies with equal weight because there are two endpoints. Another analyst says the new mean response time must be lower because 90 percent of individual requests became faster. The product owner cares about mean user wait, the 95th percentile, and how many requests a saturated deployment can complete per second.

[A24-OPERATIONS] In a separate steady operating interval after deployment, throughput and arrival rate both average 200 completed requests per second, the mean end-to-end time is 22.2 milliseconds, and the population is stable with no net buildup. You may use the accounting identity L=lambda W for this interval, where L is the mean number of requests in the system, lambda is the long-run completed-request rate, and W is mean time in seconds. No number of CPU cores, database connection capacity, service demand per resource, or saturation experiment is supplied. A hypothetical single sequential client would issue its next request only after its current request finishes, with no think time.

Please calculate the microbenchmark's complete-latency speedup and its limiting speedup if the CPU stage became arbitrarily fast. Then compute the representative replay's correct mean times, percentage change in mean time, and 95th percentiles. Explain why the average of request speedup ratios and an unweighted average of endpoint means answer different questions from the requested aggregate latency.

Finally, explain what the operating interval implies about mean in-flight requests, and what it does not establish about maximum service capacity. If you compare inverse mean latency with throughput, state the single-sequential-client assumption under which that comparison is meaningful. Recommend what evidence is still needed for the vendor's saturation-throughput claim without dismissing the real benefit observed for the fast endpoint.
''', [
    "The isolated path changes from 20 to 14 ms, for speedup 20/14≈1.4286; eliminating CPU time entirely limits this path's speedup to 20/12≈1.6667.",
    "Count-weighted replay means are 19 ms before and 22.2 ms after, a 16.84 percent increase in mean latency despite most requests improving.",
    "The specified 95th percentile is 100 ms before and 150 ms after.",
    "Mean per-request speedup ratio is about 1.1917 but is not the ratio of aggregate times or evidence of a lower count-weighted mean; equal endpoint weights also misrepresent the 900/100 request population.",
    "The stable operating identity gives mean in-system requests 200×0.0222=4.44, with milliseconds converted to seconds.",
    "Observed throughput 200/s is not a demonstrated saturation capacity; resource demand, concurrency limits, bottlenecks, and a capacity/load experiment are missing.",
    "Inverse mean latency gives a throughput relationship for a single sequential no-think-time client (about 52.63/s before and 45.05/s after for the replay mix), not arbitrary concurrent deployment capacity.",
    "Keep the two experiments scoped separately and acknowledge that the fast endpoint improved even as the workload mean and tail worsened."
], ["Do not treat CPU speedup as complete-path speedup.", "Do not assume throughput is always the reciprocal of mean latency regardless of concurrency."],
["Claims overall mean latency improved because 90 percent of requests improved.", "Calls the average of per-request speedups the actual aggregate time speedup.", "Infers saturated capacity solely from L=lambda W or the supplied 200/s observation."],
source_ids=["A24-MICRO","A24-WORKLOAD","A24-DASHBOARD","A24-OPERATIONS"], complexity_features=["serial bottleneck limit", "weighted estimands", "ratio noncommutativity", "tail latency", "units in queue accounting", "capacity identification"],
source_expectations=["Keep A24-MICRO, A24-WORKLOAD, and A24-OPERATIONS observations distinct instead of deriving unstated resource-capacity facts."], verification=["Executed serial-stage speedups, weighted replay summaries, ratio comparison, and mean-occupancy calculation."])
write_outputs()


a25_code=r'''
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
'''
a25_out=execute("A25","python",a25_code)
check("A25","full coroutine and task cache trace",a25_out,
"first loaded:x\nsecond-error RuntimeError\nshield False cached-cancelled True\nevents fetch:start,fetch:finally,A:cancelled,B:cancelled\nlater cancelled\nshield True cached-cancelled False\nevents fetch:start,A:cancelled,fetch:finally,B:loaded\nlater loaded")
add("A25", "python_async_cache_reuse_shared_cancellation_and_lifecycle", f'''
This is an original synthetic Python 3.12 incident packet involving an asynchronous metadata cache. The team made two successive changes that fixed different symptoms and now wants a single explanation of their behavior. The fixtures run in one event loop at a time. No thread modifies a cache, no external timeout is active, and the cache check and create_task insertion contain no await. Treat each shared_task call as an independent experiment.

[A25-CODE]

{fence(a25_code,"python")}

[A25-INTENT] Concurrent requests for the same key should share one in-flight fetch. Cancelling one request must not cancel another request's useful fetch. A later request should be able to reuse a successful result, but a transient fetch failure or cancellation must not poison that key indefinitely. The production result also has a time-to-live. If all consumers disappear, the team wants a deliberate policy for continuing or cancelling background work rather than an accidental consequence of whichever consumer awaited last. The example intentionally leaves that lifecycle policy unimplemented.

[A25-CLAIMS] The first patch used lru_cache directly on the async function and called the result “a cached value.” The second patch cached a Task and assumed every waiter had its own cancellation state because it had its own reader coroutine. A proposed final patch wraps awaits in shield and declares the entire cache problem solved. One reviewer says shield makes the fetch impossible to cancel even during explicit cache eviction or application shutdown. Another proposes unconditionally deleting cache[key] from any old task's completion callback, without checking whether a newer task has already replaced that entry.

Please explain the output of the coroutine-cache example and both shared-task runs, including the later lookup. Distinguish a coroutine object, a Task representing one execution, and a reusable result value. Account for cancellation propagation through an unshielded await and the different boundary created by shield. The two sleep calls are merely there to establish that both readers and the fetch have started before A is cancelled; do not attribute any real cache TTL to them.

Then evaluate the proposed final patch against the entire stated intent. Describe a concrete lifecycle design for in-flight sharing, successful result expiry, failed-task eviction, and cancellation ownership. Explain why a completion callback should confirm that it is still removing the same cached task and why a shielded caller can still receive cancellation even while useful work continues. We need to understand which failures the fixture proves and which production concerns need explicit design. Do not claim that shielding creates a fresh fetch, prevents all cancellation, makes a single-process dictionary a distributed cache, or automatically records exceptions from abandoned background tasks.
''', [
    "lru_cache stores the raw coroutine object, so the first await succeeds and the second attempt to await the already-used coroutine raises RuntimeError.",
    "Without shielding, A's cancellation propagates to the shared Task; fetch finally runs, both A and B observe cancellation, and the cached Task remains cancelled.",
    "The later unshielded-cache lookup returns that same cancelled Task and raises cancellation again rather than starting a new fetch.",
    "With shielding, A observes its own cancellation while the shared fetch survives; setting the gate allows B to get loaded and a later await reuses the completed result.",
    "shield creates a cancellation boundary for that await but does not make the underlying task immune to direct cancellation, eviction policy, or event-loop shutdown.",
    "A complete design separates in-flight task ownership from successful cached values/expiry and evicts or otherwise retries failed and cancelled work under an explicit policy.",
    "Eviction callbacks should check entry identity or generation before deleting, so an old task cannot remove a newer replacement for the same key.",
    "Account for abandoned-task exception observation and the all-consumers-gone policy; shield alone does not implement TTL, lifecycle management, or cross-process deduplication."
], ["Do not call the lru_cache entry an already computed reusable value.", "Do not claim each waiter owns a private copy of the shared Task.", "Do not interpret shield as total cancellation immunity."],
["Says the second await of the cached raw coroutine succeeds.", "Says B survives A cancellation in the unshielded run.", "Claims shield alone satisfies every cache lifecycle requirement."],
source_ids=["A25-CODE","A25-INTENT","A25-CLAIMS"], complexity_features=["three kinds of cached object", "shared cancellation", "shield ownership boundary", "stale cleanup race", "resource lifecycle"],
source_expectations=["Use A25-CODE for exact outcomes and A25-INTENT for the additional TTL and cancellation-ownership requirements."], verification=["Executed coroutine-reuse failure, both cancellation-sharing runs, and later lookups; exact trace asserted."])


a26_schema=r'''
CREATE TABLE signup(user_id INTEGER PRIMARY KEY, signup_day TEXT);
CREATE TABLE activity(event_id INTEGER PRIMARY KEY, user_id INTEGER, at TEXT);
INSERT INTO signup VALUES(1,'2026-01-01'),(2,'2026-01-01'),(6,'2026-01-01'),(3,'2026-01-02'),(4,'2026-01-05'),(5,'2026-01-08');
INSERT INTO activity VALUES
(101,1,'2026-01-08 09:00:00'),(102,1,'2026-01-08 15:00:00'),
(103,2,'2026-01-07 10:00:00'),(104,3,'2026-01-09 12:00:00'),
(105,4,'2026-01-08 10:00:00'),(106,5,'2026-01-09 10:00:00');
'''
a26_bad=r'''
SELECT COUNT(a.event_id) AS returning_events, COUNT(DISTINCT s.user_id) AS users,
       1.0*COUNT(a.event_id)/COUNT(DISTINCT s.user_id) AS retention
FROM signup s
LEFT JOIN activity a ON a.user_id=s.user_id
 AND date(a.at)=date(s.signup_day,'+7 days')
 AND a.at < '2026-01-10 00:00:00';
'''
a26_fix=r'''
WITH eligible AS (
 SELECT user_id,signup_day FROM signup
 WHERE datetime(signup_day,'+8 days') <= '2026-01-10 00:00:00'
), flag AS (
 SELECT s.user_id,s.signup_day,EXISTS(
  SELECT 1 FROM activity a WHERE a.user_id=s.user_id
  AND date(a.at)=date(s.signup_day,'+7 days')
  AND a.at < '2026-01-10 00:00:00') AS retained
 FROM eligible s
)
SELECT SUM(retained),COUNT(*),1.0*SUM(retained)/COUNT(*) FROM flag;
'''
check("A26","faulty overall numerator denominator",sql_check("A26",a26_schema,a26_bad),[[3,6,.5]])
check("A26","correct overall numerator denominator",sql_check("A26",a26_schema,a26_fix),[[2,4,.5]])
a26_cohort_query = a26_fix.replace("SELECT SUM(retained),COUNT(*),1.0*SUM(retained)/COUNT(*) FROM flag;", "SELECT signup_day,SUM(retained),COUNT(*),1.0*SUM(retained)/COUNT(*) FROM flag GROUP BY signup_day ORDER BY signup_day;")
check("A26","mature cohort proportions",sql_check("A26",a26_schema,a26_cohort_query),[["2026-01-01",1,3,1/3],["2026-01-02",1,1,1.0]])
add("A26", "sql_retention_censoring_duplicate_events_and_cancelling_errors", f'''
This is an original synthetic retention-analysis review. Please answer in German. A dashboard's overall percentage matches a hand-checked percentage, and the developer therefore wants to approve the query. The analyst is worried that two different mistakes have happened to cancel in that one scalar. The supplied tables are the entire dataset, and all timestamps and calendar dates are UTC with no daylight-saving conversion.

[A26-DATA]

{fence(a26_schema,"sql")}

[A26-METRIC] Exact day-7 retention means that a user had at least one activity event on the UTC calendar date seven days after signup. It does not mean any return within seven days, and multiple qualifying events from one user count only once. Signup date is day zero. The extract is complete for event timestamps strictly before 2026-01-10 00:00:00 UTC and includes nothing at or after that cutoff. A cohort's day-7 outcome is eligible for the requested fully observed comparison only after its entire day-7 calendar day has ended. The overall rate must weight eligible users, not give each cohort equal weight.

[A26-QUERY] The current overall calculation is:

{fence(a26_bad,"sql")}

[A26-REVIEW] The developer sees 50 percent and compares it with an analyst's 50 percent. They say the matching numbers prove that COUNT on events is equivalent to COUNT on users. They also classify every user from the January 5 and January 8 signup cohorts as “not retained,” because no qualifying day-7 event is present. A proposed visual repair hides those recent cohorts from a chart after computing the overall number, without changing the denominator. Another reviewer proposes averaging displayed cohort percentages equally because that seems simpler than carrying user counts.

[A26-BOUNDARY] User 2's event occurred on day 6 and is not a day-7 success. User 4 and user 5 have real observed activity, but their complete day-7 windows fall beyond the extract cutoff. Their future day-7 outcomes are unknown in this packet, not asserted to be failures. There is no missing ingestion before the cutoff and no rule excluding user 6 merely because that user has no activity rows. We are examining maturity of the outcome window and event-to-user aggregation, not a late-arriving-data issue.

Explain the numerator and denominator of the current query, the eligible population under the metric contract, and the correct overall numerator and denominator. Show why the two overall percentages coincide here despite different underlying counts. Give the correct retained count, denominator, and rate for each fully observed cohort, and state how the recent cohorts should be represented in a report.

Then provide a corrected query or precise query plan that first establishes eligibility and gives each user one day-7 indicator. Explain why hiding rows only after aggregation is insufficient and why equally averaging cohort rates changes the estimand. Include a boundary condition that would correctly handle a signup whose day-7 date begins exactly at the extract cutoff. We need the logic and audit trail, not only the final 50 percent, because this coincidence will not hold when the next batch of events arrives.
''', [
    "Respond in German and distinguish event counts from retained-user counts.",
    "Current query counts three qualifying activity rows over six distinct signups, giving 50 percent.",
    "Fully observed eligible users are ids 1,2,6 from January 1 and id 3 from January 2; only ids 1 and 3 are retained, giving 2/4=50 percent.",
    "The equality of the percentages is accidental: duplicate qualifying events inflate the numerator while immature users inflate the denominator.",
    "January 1 cohort is 1 retained out of 3, about 33.33 percent; January 2 is 1 out of 1, 100 percent; recent cohorts are not yet fully observed rather than zero-retention failures.",
    "An appropriate query filters signups by the end of day 7 (signup midnight plus 8 days <= cutoff), then uses EXISTS or an equivalent one-per-user retained indicator before aggregation.",
    "A cohort whose day-7 day starts at the cutoff is not fully observed; user 2's day-6 return does not qualify and user 6 remains in the eligible denominator.",
    "Compute the overall rate from eligible user totals; merely hiding cohorts after aggregation leaves the wrong population, and equal-cohort averaging gives a different target (here about 66.67 percent)."
], ["Do not classify unobserved future outcomes as failures.", "Do not treat equal final percentages as validation of their underlying counting logic."],
["Claims all six signups are eligible.", "Counts user 1 twice in the correct numerator.", "Endorses hiding chart rows without repairing the aggregate denominator."],
constraints={"language":"German"}, source_ids=["A26-DATA","A26-METRIC","A26-QUERY","A26-REVIEW","A26-BOUNDARY"], complexity_features=["right-censored outcomes", "calendar eligibility boundary", "duplicate event fanout", "errors cancelling in aggregate", "population weighting"],
source_expectations=["Use A26-METRIC for eligibility and counting units, and distinguish unknown future outcomes from complete ingestion before the cutoff."], verification=["Executed faulty and corrected SQLite queries, verifying the coincident 3/6 and 2/4 overall results."])


F=fractions.Fraction
a27_prior=F(1,10)
a27_trace=[]
for alarm in [True,False,True]:
    predicted=a27_prior*F(4,5)+(1-a27_prior)*F(1,20)
    ld,ln=(F(9,10),F(1,10)) if alarm else (F(1,10),F(9,10))
    posterior=predicted*ld/(predicted*ld+(1-predicted)*ln)
    a27_trace.append({"prediction":str(predicted),"posterior":str(posterior),"posterior_float":float(posterior)})
    a27_prior=posterior
a27_forecast=F(1,20)+F(3,4)*a27_prior
check("A27","first alarm posterior",a27_trace[0]["posterior"],"9/16")
check("A27","quiet posterior",a27_trace[1]["posterior"],"151/1672")
check("A27","final alarm posterior",a27_trace[2]["posterior"],"35433/64936")
check("A27","next-minute prior",str(a27_forecast),"596431/1298720")
check("A27","incorrect static-state posterior",str(F(1,10)*F(9,10)*F(1,10)*F(9,10)/(F(1,10)*F(9,10)*F(1,10)*F(9,10)+F(9,10)*F(1,10)*F(9,10)*F(1,10))),"1/2")
VERIFICATIONS["A27"]["filter_trace"]=a27_trace
add("A27", "probability_hidden_state_filtering_prediction_and_decisions", '''
This is an original synthetic machine-monitoring problem. A detector observes a machine whose state can change between readings. An engineer has treated three readings as repeated tests of one fixed state; another has thrown away the earlier readings and used only the latest alarm. We need to understand a sequential model well enough to decide when an immediate inspection is justified. This is not a medical diagnostic example.

[A27-STATE] At time zero, the probability the machine is degraded is 0.10. At every integer minute, the state changes before that minute's observation. If it was degraded in the previous minute, it remains degraded with probability 0.80. If it was normal, it becomes degraded with probability 0.05. The complementary probabilities produce a normal state. The transition rule is the same at every minute. No maintenance action occurs during the supplied three observations.

[A27-SENSOR] The detector alarms with probability 0.90 if the current state is degraded and with probability 0.10 if it is normal. Quiet probabilities are therefore 0.10 and 0.90. Given the entire sequence of hidden states, the observations at different minutes are independent and depend only on the corresponding current state. This does not assert that observations are marginally independent, nor that all three observations measure the same unchanging state.

[A27-OBSERVATIONS] The actual sequence is an alarm at minute 1, quiet at minute 2, and an alarm at minute 3. At the moment of the minute-2 decision, the minute-3 alarm has not yet occurred and is not available to the operator. For the arithmetic, treat all probabilities as known exactly. You may give decimal probabilities rounded to four significant digits, but retain enough precision internally to avoid an artificial change in the decision.

[A27-DECISION] At the current minute, the operator can pay 3 cost units for a perfect immediate inspection that resolves and removes any current degradation before it causes a loss. Otherwise, allowing the current minute's operation incurs 20 cost units if the machine is currently degraded and zero if it is normal. There are no other current-minute costs. For this decision only, ignore future losses, inspection capacity, and downtime. Separately, management asks for the probability of degradation at minute 4 before seeing its reading if no intervention occurs. These are intentionally different time horizons.

[A27-CLAIMS] One engineer multiplies the three degraded-state likelihoods and three normal-state likelihoods using the time-zero prior, obtaining 50 percent degraded after the sequence. They say the quiet reading cancels one alarm and the final alarm is simply a fresh repeat. A second engineer resets the prior to 0.10 before every reading. A manager says a probability is not a decision and refuses to compare the inspection cost with an expected loss. Another analyst proposes using the minute-3 alarm to describe the information actually available when the minute-2 action was taken.

Please calculate, for each minute, the predicted degradation probability before observing the detector and the updated probability after that minute's observation. Explain the predict-then-update sequence and where both engineers' methods change the stated model. Give the minute-4 prediction under no intervention. Then derive the current-minute inspection threshold from the supplied costs and state the decisions after minutes 2 and 3. Distinguish filtering with observations available now from retrospective inference that uses future observations, and make clear why the minute-4 prediction is not a replacement for the minute-3 probability in the immediate decision.
''', [
    "Use prediction p_minus=0.80p+0.05(1-p)=0.05+0.75p before each observation, then update by the appropriate alarm/quiet likelihoods.",
    "Minute 1 prediction is 0.125 and alarm posterior is 0.5625.",
    "Minute 2 prediction is 0.471875 and quiet posterior is 151/1672≈0.09031.",
    "Minute 3 prediction is 0.05+0.75×(151/1672)≈0.117733 and alarm posterior is 35433/64936≈0.5456603.",
    "No-intervention minute-4 prediction is 596431/1298720≈0.4592453, applying one further transition without an observation.",
    "The fixed-state likelihood calculation gives 0.5 but assumes one unchanged state; resetting to 0.1 discards the previous posterior and the transition dynamics.",
    "Inspect when 20p exceeds 3, or p>0.15; after minute 2 do not inspect under this simplified rule, while after minute 3 inspect.",
    "Minute-2 real-time filtering cannot use minute-3 evidence; using future data would be retrospective smoothing, and next-minute prediction concerns a different state/time horizon from the current-minute decision."
], ["Do not multiply observations as repeated tests of a fixed state under the supplied transition model.", "Do not import future evidence into a historical real-time decision."],
["Reports 0.5 as the correct final filtering probability.", "Skips the transition before the first observation.", "Uses minute-4 risk for the current-minute cost calculation without changing the decision problem."],
source_ids=["A27-STATE","A27-SENSOR","A27-OBSERVATIONS","A27-DECISION","A27-CLAIMS"], complexity_features=["latent state transitions", "conditional versus marginal independence", "sequential Bayes updates", "filtering versus smoothing", "cost-derived threshold"],
source_expectations=["Use the complete synthetic state and sensor model and distinguish the immediate cost contract from the separate no-intervention forecast."], verification=["Executed exact Fraction-based filtering and forecasting plus the incorrect static-state comparison."])
write_outputs()


def a28_merge(left,right):
    return (left[0]|right[0],left[1]|right[1])
def a28_visible(state):
    return sorted({item for item,tag in state[0] if tag not in state[1]})
a28_r1=({("apple","a0"),("apple","a1")},{"a0"})
a28_r2=({("apple","a0"),("apple","b1")},{"a0","b1"})
a28_merged=a28_merge(a28_r1,a28_r2)
check("A28","visible items after merge",a28_visible(a28_merged),["apple"])
check("A28","live tags after merge",sorted(tag for item,tag in a28_merged[0] if tag not in a28_merged[1]),["a1"])
check("A28","commutative merge",a28_merge(a28_r1,a28_r2)==a28_merge(a28_r2,a28_r1),True)
check("A28","idempotent duplicate merge",a28_merge(a28_merged,a28_r2)==a28_merged,True)
a28_compacted=(set(),set())
a28_offline=({("apple","a0")},set())
check("A28","unsafe compaction resurrection",a28_visible(a28_merge(a28_compacted,a28_offline)),["apple"])
add("A28", "distributed_observed_remove_sets_causality_and_tombstone_gc", '''
This is an original synthetic replicated-cart protocol. It models whether an item is present, not an item's numeric quantity. No commercial database behavior is implied. The team claims its union-based merge makes everything safe to delete locally once an item is removed, but an offline replica later brought an old item back. We want to understand which behavior is part of the chosen conflict rule and which behavior indicates unsafe metadata cleanup.

[A28-STATE] A replica stores two sets: Adds contains pairs (item, unique_tag), and Removed contains tags. An item is visible if at least one of its add tags is not in Removed. Every new local add creates a globally unique tag; redelivery of an existing add keeps its original tag. Removing an item adds to Removed all tags for that item currently known in that replica's Adds. The remove does not invent tags for adds the replica has not seen. To merge states, take set union of Adds and set union of Removed. The sets themselves are unbounded unless a separate cleanup protocol is introduced.

[A28-PARTITION] Replicas R1 and R2 initially share Adds={(apple,a0)} and Removed={}. They disconnect. R1 removes apple, recording a0, then re-adds apple with new tag a1. Independently, R2 adds apple with new tag b1 and then removes apple, recording every apple tag it currently knows. Neither replica sees the other's new tag before reconnection. The operations listed on each replica occur in that local order. Wall-clock timestamps differ across machines and have no role in this protocol.

[A28-MERGE] After reconnection, each replica receives the other's full state, possibly twice and in either message order. No new user operation occurs after the local actions described above. A reviewer believes R2's last remove must win globally because it was the last button press on that replica. Another believes two add tags necessarily mean quantity two, even though the UI displays only item membership. A third says retrying a delivered message should create another tag because a network delivery is “another add.”

[A28-CLEANUP] Consider a separate cleanup experiment, not additional operations on the merged state. R2 has Adds={(apple,a0),(apple,b1)} and Removed={a0,b1}, so apple is absent there. R2 deletes both matching add entries and their removal markers, leaving both sets empty. Replica R3 has been offline since the initial state and still has Adds={(apple,a0)}, Removed={}. Later R3 reconnects and its old state is merged with R2. No protocol has confirmed that R3 received the remove, no replica-membership retirement has occurred, and old messages can still be delivered.

Please derive each partitioned replica's state and the merged visible membership. Explain whether duplicate or reordered state messages change that result, and identify the tag that determines apple's final presence. Then assess the review claims using the specified observed-remove rule, including the difference between a fresh user add and a retried network delivery.

Work through the separate cleanup experiment and explain why deleting removal evidence locally can resurrect a removed item. Describe what kind of causal-stability, acknowledgement, replica-retirement, or epoch protocol would be needed to justify safe reclamation in an actual design. Finally, distinguish convergence under the defined merge from stronger promises such as a globally latest wall-clock remove, item quantity, inventory reservation, or immediate consistency while disconnected. We want the exact contract we built, not a generic claim that conflict-free data types eliminate every conflict.
''', [
    "R1 ends with adds a0/a1 and removed a0; R2 ends with adds a0/b1 and removed a0/b1.",
    "Merged state contains adds a0,a1,b1 and removals a0,b1, leaving a1 live and apple present.",
    "R2's remove cannot name unseen a1, so it does not globally defeat that concurrent re-add; wall-clock or last-local-button order is not the protocol's conflict rule.",
    "Set-union merge is commutative and idempotent, so duplicate/reordered state delivery does not change this result.",
    "A retransmitted add preserves its tag; a fresh user add gets a new tag. The membership data type does not define numeric quantity from the number of tags.",
    "In the separate cleanup experiment, merging offline R3's surviving a0 into an empty compacted R2 makes apple visible again because the a0 tombstone was discarded.",
    "Safe reclamation needs evidence that obsolete adds cannot reappear from any relevant replica or message, with a sound causal acknowledgement/retirement/epoch policy; local absence alone is insufficient.",
    "Convergence under this merge is distinct from remove-wins total order, immediate disconnected consistency, quantity accounting, or inventory reservation guarantees."
], ["Do not apply the separate cleanup experiment as if it occurred after the earlier merged state.", "Do not silently replace the observed-remove rule with a last-writer-wins rule."],
["Claims apple is absent after the first merge.", "Claims deleting both an add and its tombstone locally is always safe.", "Treats network redelivery as a new unique-tag user action."],
source_ids=["A28-STATE","A28-PARTITION","A28-MERGE","A28-CLEANUP"], complexity_features=["causal visibility", "concurrent remove and re-add", "idempotent merge", "separate counterexample", "metadata reclamation"],
source_expectations=["Ground all behavior in the invented set algebra and distinguish state convergence from additional unstated application guarantees."], verification=["Executed set unions, visible-tag derivation, commutativity/idempotence checks, and unsafe-compaction resurrection."])


a29_tokens={
    "T1":{"aud":["reports-ui"],"exp_delta":300,"scopes":["inventory:read"]},
    "T2":{"aud":["inventory-api"],"exp_delta":-20,"scopes":["inventory:read"]},
    "T3":{"aud":["inventory-api"],"exp_delta":300,"scopes":["inventory:read"]},
    "T4":{"aud":["inventory-api"],"exp_delta":300,"scopes":["inventory:write"]},
}
a29_current={};a29_policy={}
for name,t in a29_tokens.items():
    gateway=t["exp_delta"]>=-30
    backend="inventory:read" in t["scopes"]
    a29_current[name]=gateway and backend
    a29_policy[name]=("inventory-api" in t["aud"] and t["exp_delta"]>0 and backend)
check("A29","deployed acceptance",a29_current,{"T1":True,"T2":True,"T3":True,"T4":False})
check("A29","policy acceptance",a29_policy,{"T1":False,"T2":False,"T3":True,"T4":False})
add("A29", "technical_authorization_source_conflict_and_deployed_behavior", '''
This is an original synthetic authorization-review packet. The service, token claims, policy names, and version history are invented. No real credentials are included. We need an explanation of whether observed successful requests comply with our stated policy, and which configuration actually governs them. The question is about reasoning from the supplied evidence, not attempting requests against any live service.

[A29-POLICY7] Security contract revision 7, effective before the incident, applies to GET /v2/inventory. Acceptance requires a valid signature from issuer corp, an audience array containing the exact value inventory-api, current time strictly earlier than exp, and scope inventory:read. For this contract there is no expiration grace period. A scope of inventory:write does not implicitly include inventory:read. The policy is normative: it states what requests should be accepted, not what the current binaries necessarily implement.

[A29-DEPLOYMENT] The incident occurs at 2026-11-16 12:00:00 UTC. Gateway build 2.6 verifies the signature and issuer. Its active configuration is audienceRequired=false and expirationLeewaySeconds=30. When audienceRequired is false, it does not check the audience claim. Its expiry predicate accepts if now is less than or equal to exp+30 seconds. The backend build 4.2 trusts the gateway's authentication decision and checks only for exact inventory:read scope on this route. The trace confirms these binaries and this configuration were active; there is no other hidden verifier.

[A29-DOCS] SDK 2.6 reference documentation accurately says audience checking is optional and disabled by default. That statement describes the SDK option, not an exception to revision 7. Release notes for gateway 2.7 say audience checking becomes mandatory, but 2.7 has not been deployed. A current website page describes policy revision 8, effective December 1, 2026, introducing an additional hardware-proof requirement for /v3/write routes. It does not retroactively change revision 7 or the /v2/inventory route in this packet.

[A29-TOKENS] Assume all four signatures are valid and issuer is corp:

| Token | Audience array | Expiration relative to incident time | Scope list |
|---|---|---:|---|
| T1 | [reports-ui] | 300 seconds later | [inventory:read] |
| T2 | [inventory-api] | 20 seconds earlier | [inventory:read] |
| T3 | [inventory-api] | 300 seconds later | [inventory:read] |
| T4 | [inventory-api] | 300 seconds later | [inventory:write] |

[A29-TRACE] T1, T2, and T3 received successful backend responses. T4 passed the gateway but the backend returned a scope-denied response. A developer calls these successes proof of policy compliance because the tokens were signed. Another says the SDK's optional setting overrules the security policy. A reviewer insists every request is invalid because the newest website mentions hardware proof. Someone else recommends waiting for the planned 2.7 rollout and considers the expiration discrepancy resolved automatically by that release note.

Please give an acceptance matrix for the deployed implementation and for the applicable policy, explaining each mismatch by claim and enforcement layer. Distinguish signature authenticity, intended audience, expiration, and route authorization rather than collapsing them into “valid token.” Evaluate the four comments using source scope, deployment version, effective date, and route.

Then propose concrete configuration and verification steps that bring this route into compliance. Explain what the observed acceptance proves about behavior and what it does not prove about policy. Include how you would test the audience mismatch, the expiration boundary, and the scope distinction after a fix. If you recommend backend verification or relying on a gateway boundary, state the relevant trust-path assumption; do not assert an unseen direct-backend bypass exists. Cite supplied evidence IDs for the main conclusions.
''', [
    "Deployed behavior accepts T1,T2,T3 and rejects T4 at the backend; this matches the trace.",
    "Revision 7 permits only T3: T1 has the wrong audience, T2 is expired with no policy grace, and T4 lacks read scope.",
    "A valid signature and issuer establish authenticity under the supplied assumptions but do not satisfy audience, time, or route-scope requirements.",
    "SDK optional behavior describes available implementation configuration and does not override the normative policy; undeployed 2.7 behavior is not current enforcement.",
    "Revision 8's later effective date and /v3/write scope do not impose hardware proof on this incident's /v2/inventory route.",
    "Enable and configure exact expected audience enforcement and align expiration behavior with strict now<exp; merely setting leeway to zero still requires attention to the implementation's <= boundary.",
    "Preserve the exact read-scope check and verify wrong audience, already expired, exactly-at-exp, valid future expiry, and write-only scope cases; the 2.7 audience note alone says nothing about fixing expiry semantics.",
    "Tie conclusions to the supplied evidence and specify a sound trust-path assumption for gateway-only versus backend verification without inventing an observed bypass."
], ["Do not infer authorization from signature alone.", "Do not treat the future/latest document as automatically governing the deployed route.", "Do not assume a zero leeway fixes a <= versus < equality mismatch."],
["Calls T1 or T2 compliant with revision 7.", "Rejects T3 solely for lacking the future hardware proof.", "Claims undeployed gateway 2.7 already protects the current route."],
constraints={"require_table":True}, source_ids=["A29-POLICY7","A29-DEPLOYMENT","A29-DOCS","A29-TOKENS","A29-TRACE"], complexity_features=["normative versus observed truth", "version and effective-date conflicts", "layered predicates", "expiry boundary", "route-specific scope"],
source_expectations=["Use A29-POLICY7 for the normative matrix, A29-DEPLOYMENT/A29-TRACE for actual behavior, and A29-DOCS only within its version/date/route scope."], verification=["Executed the deployed and normative acceptance predicates for all four synthetic claim packets."])


a30_electric={"Alpha":100*1000*400/1000,"Beta":20*1000*100/1000,"Gamma":40*1000*250/1000}
a30_low=sum(a30_electric.values())+2000*2
a30_high=a30_low+3000*2
a30_units=100000+10000+40000
check("A30","electric emissions kg",a30_electric,{"Alpha":40000,"Beta":2000,"Gamma":10000})
check("A30","total current emissions bounds kg",[a30_low,a30_high],[56000,62000])
check("A30","current fleet intensity bounds kg per shipment",[a30_low/a30_units,a30_high/a30_units],[28/75,31/75])
check("A30","baseline intensity",70000/200000,.35)
check("A30","relative intensity increase lower",(a30_low/a30_units)/.35-1,1/15,1e-12)
check("A30","relative intensity increase upper",(a30_high/a30_units)/.35-1,19/105,1e-12)
check("A30","absolute emissions decrease lower",1-a30_high/70000,4/35,1e-12)
check("A30","absolute emissions decrease upper",1-a30_low/70000,.2,1e-12)
check("A30","incorrect equal-site intensity",(.44+.20+.25)/3,89/300,1e-12)
add("A30", "units_weighted_intensity_missing_data_bounds_and_claim_scope", '''
This is an original synthetic sustainability-metrics review. Please answer in Portuguese. We are comparing two reporting periods for a small logistics network and need to correct a public-facing draft before it confuses lower total emissions with lower emissions per shipment. The supplied factors are invented and exact for the exercise; this is not a request to select real emissions factors or interpret a legal reporting standard.

[A30-CURRENT] Electricity and shipment totals for the current period are:

| Site | Electricity, MWh | Electricity factor, grams CO2e per kWh | Completed shipments |
|---|---:|---:|---:|
| Alpha | 100 | 400 | 100000 |
| Beta | 20 | 100 | 10000 |
| Gamma | 40 | 250 | 40000 |

Alpha also consumed exactly 2000 cubic meters of gas. Beta consumed no gas. Gamma's gas meter failed, but an independent physical bound establishes that its consumption was between zero and 3000 cubic meters inclusive. The gas factor is 2 kilograms CO2e per cubic meter at every site. The bound is not a probability distribution, and no value inside it is declared more likely. One MWh is 1000 kWh, and one kilogram is 1000 grams. Both electricity and gas emissions belong in the requested operational boundary.

[A30-BASELINE] The preceding period's verified network total for the same included activities and site set was 70000 kilograms CO2e and 200000 completed shipments. The current period has 150000 completed shipments across the listed sites. The shipment definition is unchanged. The baseline includes complete gas data, but site-level baseline emissions, site-level baseline shipment counts, and baseline electricity factors are not available in this packet. Do not infer that site mix or electricity factors stayed constant merely because the sites themselves did.

[A30-DRAFT] The author divides each site's reported emissions by that site's shipment count, assigns Gamma zero gas, and takes an unweighted average of the three site intensities. They call that the network intensity and compare it with baseline total emissions divided by baseline total shipments. They also write: “Total emissions fell, proving operational efficiency improved. Gamma's missing value can be set to zero because nothing was recorded. The midpoint of its bound is our statistically expected gas use, and the range gives a 95 percent confidence interval.” None of those extra statistical assumptions appears in the measurement packet.

[A30-DECISION] We need a network-level comparison using total included emissions divided by total completed shipments. The report may show a bounded range while the gas data is unresolved. It should separately communicate absolute emissions and per-shipment intensity. The communications team also wants to know whether the observed change establishes that processes at individual sites became more efficient, rather than output volume, site mix, energy mix, or factors changing. That stronger attribution would require evidence beyond a correctly calculated ratio.

Please compute current electricity emissions by site, the current total-emissions bound including gas, and the corresponding network intensity bound in kilograms CO2e per shipment. Compare both absolute emissions and intensity with the baseline, expressing the direction and approximate relative percentage change. Explain why the unweighted site average is not the requested network rate and why the observed lower volume matters.

Then assess every quoted claim about the missing meter, midpoint, confidence level, and efficiency. Give wording that would accurately communicate the supported comparison without implying a causal site-efficiency result. Identify what additional disaggregated measurements would distinguish a process improvement from a change in the composition of activity, and keep worst-case bounds distinct from probability statements throughout.
''', [
    "Respond in Portuguese and correctly convert MWh to kWh and grams to kilograms, giving electricity emissions Alpha 40000 kg, Beta 2000 kg, Gamma 10000 kg CO2e.",
    "Alpha gas adds 4000 kg; Gamma gas adds between 0 and 6000 kg; network emissions are therefore between 56000 and 62000 kg.",
    "Divide by 150000 shipments to get current intensity approximately 0.37333–0.41333 kg CO2e per shipment; baseline intensity is 0.35.",
    "Current absolute emissions are about 11.43–20 percent below baseline, while intensity is about 6.67–18.10 percent above baseline.",
    "The draft's equal-site average with zero Gamma gas is about 0.29667 kg per shipment and weights sites rather than shipments; the requested overall rate is a shipment-weighted combination or total over total.",
    "Missing gas is bounded unknown, not known zero; midpoint is not an expected value without a distribution and the bounds are not a 95 percent confidence interval.",
    "Volume fell 25 percent, so reduced total emissions can coexist with higher per-shipment intensity; neither ratio by itself identifies a causal process-efficiency change.",
    "Provide accurate report wording and request baseline/current site output, fuel/electricity use, factors, and relevant mix data to separate within-site changes from composition or factor changes."
], ["Do not substitute an unstated real emissions standard for the packet's boundary.", "Do not present bounded missing data as a probabilistic estimate.", "Do not compare an unweighted current site mean with a total-based baseline as the same estimand."],
["Claims network per-shipment intensity improved.", "Treats Gamma gas as known zero.", "Calls the supplied physical bounds a 95 percent confidence interval or their midpoint an established expectation."],
constraints={"language":"Portuguese"}, source_ids=["A30-CURRENT","A30-BASELINE","A30-DRAFT","A30-DECISION"], complexity_features=["compound-unit conversion", "weighted denominators", "bounded missing data", "absolute-versus-intensity reversal", "causal attribution limits"],
source_expectations=["Use A30-CURRENT for units and missing-data bounds, A30-BASELINE for the comparable historical denominator, and avoid inventing disaggregated history."], verification=["Executed emissions conversions, bound propagation, weighted intensity, baseline contrasts, and incorrect equal-site comparison."])
write_outputs()

