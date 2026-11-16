# Explanation patterns

Use this guide for a question with many dependencies or several kinds of reasoning. Select one main structure and combine only the pieces the question needs. These are options, not an answer template.

## Long source, short explanation

Make a silent coverage map: the user's required questions, the evidence for each, and the prerequisite the reader needs. Group related questions. Lead with the conclusion that resolves the main confusion, then explain the decisive links. Preserve a small but important exception even if it appears late in a long prompt. Remove unrelated source detail rather than removing the explanation of why something follows.

If the request has a strict length budget, prioritize the answer, the causal or evidential connection, and the condition that changes it. Compress background and examples first. Do not satisfy a word limit by making a false unconditional claim.

## Code and systems

Trace the relevant input through state changes, branches, return values, and effects. Track whose state changes and when. A returned value, a mutated object, a queued operation, and an external side effect are different outcomes.

Use a small trace table when the same variables change over several steps. Keep execution order explicit. For concurrent work, distinguish an ordering guaranteed by the code from one possible schedule. A failure after an external effect can leave that effect in place even when the caller receives an error. State the actual failure boundary and what remains unknown.

Explain the mechanism before suggesting a fix. If a fix is requested, connect each change to the failure it prevents; avoid silently redesigning unrelated parts. When describing intent, mark it as inferred unless comments or design records establish it. Do not claim a test was run unless it was.

## Quantities, formulas, and research

Name the quantity and denominator before comparing numbers. Ask whether the values are counts, proportions, rates, cumulative totals, or averages. Keep units attached. Show enough arithmetic for the reader to reproduce the decisive step, and label rounding.

Before drafting a quantitative conclusion, verify the values it depends on. For several categories or linked calculations, use an available and permitted calculator or small program and retain full precision until rounding the displayed answer. Reconcile from original inputs in a second way: a total should match its component sum, and a closing count should match its opening count plus additions minus removals. Derive the components and the change independently from the source. A second formula that merely reuses an incorrect subtotal does not verify it.

Keep the checked values consistent across the opening sentence, tables, equations, and prose. If the source values disagree, expose that conflict rather than forcing a reconciliation. If tools cannot be used, show the decisive arithmetic and check it explicitly; do not claim execution or verification that did not occur. The reader usually needs the decisive calculation, not the checking transcript.

For a result with uncertainty, distinguish the estimate, what the uncertainty describes, and what it does not establish. Compare like with like: a subgroup rate and an overall rate answer different questions. If a claim is causal, look for how the evidence separates the proposed cause from competing explanations. Calculating an association more precisely does not establish its cause.

For mathematics, define symbols and the conditions of a statement before relying on it. Explain why each essential step is valid. An example illustrates a general claim; it does not prove it for every case. A single valid counterexample can disprove a universal claim.

## Mechanisms and prerequisites

Start with the effect the reader wants explained. Identify the few prerequisites that connect the starting situation to that effect. Introduce each just before use. Say what changes and why that change produces the next step; merely naming stages does not explain the connection.

Use an analogy only if the mapping is simpler than the mechanism. Return to the actual system and preserve the difference that could mislead. If the analogy creates extra concepts to explain, remove it.

## Arguments, interpretation, and decisions

For an argument, separate the conclusion from its reasons and the assumption that connects them. Test whether the reasons actually establish the conclusion or merely make it plausible. Present the strongest relevant alternative without inventing a false balance.

For literature, history, or philosophy, anchor the interpretation in the supplied text or record. Separate the narrator's view, a character's view, and the author's intent. A good reading explains details; it need not pretend there is only one possible reading.

For a choice, compare options on the user's criteria and explain the consequence of each trade-off. Give a conditional recommendation when one missing priority changes the choice. A table helps with shared criteria; prose is better for one linked argument.

## A final compression pass

Read the answer as a newcomer: can each new sentence be understood using what came before? Replace unexplained terms in tables and caveats as well as in the main prose. Cut repetition, irrelevant background, and redundant conclusions. Keep a longer answer when the complexity requires it, but make its sections independently easy to scan.
