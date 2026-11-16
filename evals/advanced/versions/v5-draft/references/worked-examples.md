# Worked examples

These original examples demonstrate explanation choices. They are not facts to reuse in unrelated answers or a compulsory format. Read the example closest to the current difficulty. All named products, source excerpts, and quantitative datasets below are fictional teaching fixtures.

## 1. A small code trace: explain the visible syntax

**Request.** “Why does this print different lists? I'm new to Python.”

```python
first = [2, 4]
second = first
third = first[:]
second.append(6)
print(first, third)
```

**Example answer**

`first` and `second` refer to the same list, so adding `6` through `second` also changes what you see through `first`. `third` refers to a separate list.

| Line | What it does |
| --- | --- |
| `second = first` | Gives the existing list another name |
| `third = first[:]` | `[:]` copies the list's contents into a new list |
| `second.append(6)` | Adds `6` to the shared list |

The printed result is `[2, 4, 6] [2, 4]`. Here, the lists contain only numbers; copying a list does not recursively copy objects nested inside it.

**Choice illustrated.** Explain the relevant characters and shared object before introducing terms such as alias or shallow copy. A short boundary prevents overgeneralizing the example. This is a trace of the code, not a claim that it was executed.

## 2. A numerical comparison: preserve the denominator

**Request.** “Our fictional workshop cut damaged items from 12 out of 200 to 9 out of 300. Did damage fall by 25% or 50%?”

**Example answer**

Both numbers describe a different change: **the damaged-item count fell 25%; the damage rate fell 50%.**

| Measure | Before | After | Change |
| --- | --- | --- | --- |
| Damaged items | 12 | 9 | 3 fewer, or 25% fewer |
| Share of output damaged | 12/200 = 6% | 9/300 = 3% | Down 3 percentage points, or 50% relative to 6% |

Use the rate to compare how often damage occurred, because total production also changed. These counts show an improvement in the observed rate; they do not identify what caused it.

**Choice illustrated.** Resolve the apparent contradiction before showing arithmetic. The table compares the same criteria and keeps the baseline visible.

## 3. Conflicting documents: applicability before recency

**Supplied fictional sources.** [D1] Quill 2 contract: each request may contain at most 40 records. [D2] Quill 3 release preview: the limit will be 100 records. [D3] Deployment record: this service runs Quill 2. The user asks whether sending 70 records is supported now.

**Example answer**

**No: the documented limit for this deployment is 40 records per request.** It runs Quill 2 [D3], whose contract sets that limit [D1]. The 100-record limit belongs to the Quill 3 preview and does not change the installed version's contract [D2].

A 70-record request is therefore outside the documented limit. The supplied documents do not say whether the service rejects or truncates it, so that behavior needs the Quill 2 error specification or an observed test.

**Choice illustrated.** Cite the exact support for the conclusion and stop at its boundary. “Unsupported” does not establish a particular runtime failure.

## 4. Missing evidence: a useful conditional explanation

**Request.** “Our fictional service's typical response time fell from 180 ms to 120 ms after a cache was enabled. Explain why that proves the cache caused the improvement. Those are the only measurements.”

**Example answer**

The measurements show a 60 ms decrease, about 33% relative to 180 ms. They do **not** establish that the cache caused it.

A cache saves results for reuse. It could reduce response time by avoiding repeated work. But traffic, request mix, or other changes could also explain this before-and-after difference. The word “typical” also needs a definition: an average and a middle value summarize response times differently.

To test the cache explanation, compare otherwise similar requests with and without caching and record whether each request reused a saved result. That would connect the proposed mechanism to the measured change.

**Choice illustrated.** Correct the premise, explain the plausible mechanism, and identify the specific missing comparison without turning uncertainty into a refusal.

## 5. Interpreting a text: evidence without false certainty

**Original passage.** “Mara set the spare cup beside the door. When the last bus passed, she washed it and put it away.” The user asks whether this proves Mara has forgiven the visitor who never arrived.

**Example answer**

The passage suggests that Mara expected or hoped for a visitor, but it does not prove forgiveness.

The spare cup makes room for another person. Waiting until the last bus passes suggests she keeps that possibility open. Putting the cup away marks the end of the wait; it could express disappointment, resignation, or simply a practical decision.

Forgiveness is one possible reading if the wider story establishes a prior conflict. In these two sentences alone, the strongest supported idea is **an invitation or expectation that goes unanswered**.

**Choice illustrated.** Connect textual details to an interpretation, separate possibility from certainty, and identify which missing context matters. No mechanical process or comparison table is needed.

## 6. A direct conceptual question: stop when complete

**Request.** “What is a prerequisite? One sentence.”

**Example answer**

A prerequisite is something you need to know, have, or complete before you can do something else—for example, knowing multiplication before learning long division.

**Choice illustrated.** A simple question needs no headings, table, glossary, source hunt, or appended teaching plan. Rich reference material should improve judgment, not inflate every answer.
