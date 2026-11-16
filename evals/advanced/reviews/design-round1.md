# Independent design review — round 1

## Decision and scope

**No material factual, numerical, or code error blocks development evaluation.** The draft does not need additional domain chapters. Its main remaining content issues are small mismatches between the terminology rule and two worked examples. The protocol can support a useful comparison, but two details should be settled before validation results are used for a strong, preregistered improvement claim: the decision rule and the matching of generation conditions.

This review read only `versions/v5-draft/SKILL.md`, its three `references/*.md` files, and `evals/advanced/protocol.json`. It did not inspect prompts, gold criteria, authoring material, responses, or holdout contents. Python was used to check the visible code example, arithmetic, JSON validity, and protocol totals. No model responses were generated.

## Six worked examples

| Example | Correctness assessment | Focused change |
| --- | --- | --- |
| 1. Python list copying | The output is exactly `[2, 4, 6] [2, 4]`; assignment shares the original list and `[:]` creates another outer list. The nested-object qualification is correct. | Replace “recursively copy objects nested inside it”: this introduces an unexplained technical term in a caveat aimed at a Python beginner. |
| 2. Damage counts and rates | Count falls by `(12−9)/12 = 25%`. Rates are 6% and 3%; their difference is 3 percentage points and their relative decrease is 50%. The causal limitation is justified. | Explain “percentage points” through the subtraction, and make the relative-change calculation visible. The current table gives the answer but leaves a necessary term implicit. |
| 3. Versioned limits | Quill 2's 40-record contract applies to the recorded deployment. Seventy records exceed it. No rejection or truncation behavior can be inferred from the supplied documents. Citations support the precise claims. | No necessary change. An observed test would establish observed behavior under its conditions, not a contractual guarantee; preserve that distinction if expanding this answer. |
| 4. Cache and response time | A 60 ms decrease is approximately 33.3% of 180 ms. Before-and-after measurements do not establish causation. The ambiguity of “typical” matters. | Optional: make the proposed comparison explicitly controlled. Recording reuse connects a mechanism to observations but does not itself remove differences in traffic or workload. |
| 5. Mara and the cup | The rejection of “proves forgiveness” is sound. The passage permits the interpretations listed, and the answer names the missing prior-conflict context. | Optional: remove “invitation” from the final strongest-supported reading. An invitation is less directly supported than an expectation of a visitor. |
| 6. Prerequisite | Correct, one sentence, concrete, and proportionate. | No change. Do not attach citations, a table, or additional instructional apparatus. |

The execution check above is evidence from this review. It does not turn the example's original prose into a claim that its author executed the code.

### Suggested replacement wording

For example 1's last sentence:

> Here, the lists contain only numbers. If a list contains another list, copying the outer list this way leaves both copies referring to that same inner list.

For example 2, the last change cell can read:

> 6% − 3% = 3 percentage points; 3 ÷ 6 = 50% relative decrease.

If the intended audience is a newcomer to percentages, add a short lead-in instead of relying on the label alone:

> A percentage-point change subtracts the two percentages; a relative change compares that difference with the starting percentage.

Use whichever version fits the audience; both are unnecessary together. Also replace “Both numbers describe a different change” with “Both are correct, but they measure different changes.”

For example 4's proposed next step, if revised:

> To test the cache explanation, compare the same workload with and without caching while keeping other conditions as stable as possible, and record which requests reused a saved result.

For example 5's final sentence, if revised:

> In these two sentences alone, the strongest supported reading is that Mara expected someone and eventually stopped waiting.

## Skill robustness and instruction conflicts

### No hard contradiction found

The default length ranges have explicit exceptions for requested depth and essential reasoning. Meaning-first terminology is balanced by the instruction to preserve standard terminology for experts. Tables are conditional on shared comparison criteria; processes and interpretations have different structures. The six examples do not all use the same format. These provisions avoid a mandatory answer template.

The core is 1,472 whitespace words; the core and all references total 3,736. That size is not evidence of excessive answer length. The actual risk is whether models imitate every visible example or apply every checklist item to every question. The protocol's all-reference injection makes that a useful development observation, but it does not test the native selective-loading behavior.

### Useful improvements, not content blockers

1. **Make primary-source preference match the claim.** In `evidence-and-sources.md`, “Prefer direct, applicable primary evidence” works for code behavior, a contract, or an individual study. It should not suggest that one original study automatically outranks an applicable synthesis when the question concerns a body of research. A compact addition is sufficient:

   > Match the source type to the claim: an original study supports its reported findings; a reliable synthesis can support claims about a body of evidence. Being primary does not by itself make a source stronger or more applicable.

   This is an evidence-selection clarification, not a request for a catalogue of research methods.

2. **Make the absent-material rule consistently conditional.** Section 1 asks for clarification only when missing context prevents a useful, accurate answer. Section 2's “If the user points to absent material, request it” could be read as requiring a question even when the remaining request is answerable. The surrounding paragraph already encourages a supported partial answer, so this is a small ambiguity rather than an actual conflict. Suggested replacement:

   > If essential referenced material is absent, explain what can be supported without it, name the gap, and request the material when it prevents a useful, accurate answer.

3. **Preserve conditions when presenting the answer first.** The opening-first rule should not make a later qualification reverse the opening. The existing evidence and simplification rules mostly cover this. If development responses exhibit this failure, add one sentence rather than another section:

   > Put a condition or uncertainty that changes the answer in the opening, rather than correcting an unconditional opening later.

4. **Keep the existing terminology audit broad.** Its explicit coverage of tables, examples, and caveats addresses a real consistency risk. Fixing examples 1 and 2 is more useful than adding further terminology instructions.

No additional generic glossary, analogy quota, heading quota, citation quota, or universal worked-example requirement is warranted. The existing rules already cover supplied-source injection, unseen runtime behavior, concurrent ordering, misleading causal premises, mathematical proof versus illustration, and interpretation versus established fact.

## Protocol validity

### Mechanical checks

`protocol.json` parses. The 36 development, 12 validation, and 12 holdout cases sum to 60. Six dimensions with a maximum of two points give the stated maximum of 12. B19 through B30 names 12 identifiers. The pass threshold, critical-error override, fallible-gold provision, and requirement to regenerate a changed final bundle for full-release aggregates are internally compatible.

Those checks establish only consistency of the protocol text. They do not establish that registration preceded generation, that the splits are sealed, or that the eventual records follow the protocol.

### Claim blockers to settle before validation

**1. Specify what result warrants the intended improvement claim.** The protocol defines individual pass/partial/fail decisions but not the primary aggregate comparison or a release decision rule. This is not a blocker to development generation. It leaves room to select a favorable metric after seeing validation results.

Suggested addition:

> Report the final candidate's per-case outcomes alongside the frozen baseline, with paired wins, ties, and regressions by split. Treat critical failures and essential-answer regressions separately from total scores. Before validation, record whether selection is descriptive or governed by a specified release rule; do not choose the primary success metric after seeing validation or holdout results.

A numerical superiority threshold is optional if the work makes only descriptive claims. If a threshold is used, choose it prospectively. Twelve holdout cases are limited evidence; a clean result should not become a claim of universal reliability.

**2. Match and record generation conditions.** Fresh contexts containing up to six cases still permit within-batch influence. The protocol randomizes review records but does not explicitly match generation batch composition, case order, exposed model settings, tool access, or output budgets across variants. Unequal conditions could explain an apparent skill effect.

Suggested addition:

> Use the same case batches and case order for baseline and candidate, with the same exposed model configuration, tool policy, and output budget. Record unavailable settings as unknown. Preserve the exact ordered input packet and run metadata for each batch; report batch context as a dependence when interpreting results.

Also bind each response to its prompt/input-packet hash and bundle hash, and each review to its response hash, gold version, and rubric version. Existing response hashes alone cannot detect a review against the wrong revised gold. This extends the current integrity scheme rather than requiring new testing infrastructure.

### Useful protocol clarifications

- **Separate hard constraints from preferences.** “Exactly one sentence” and “under 200 words” are hard constraints; “roughly 200 words” is not an exact count boundary. Apply the explicit-constraint failure override to the former and assess reasonable variation in the latter under fit. Record that distinction in the criteria before reviewing responses.
- **Keep simple-question claims separate.** A minimum of 400 prompt words makes this a long-request evaluation. It does not test whether the expanded skill remains brief on a natural short question. The limitation is acceptable for this objective. If the release makes a broader brevity claim, a small separately reported short-prompt check would address it; do not pad short questions merely to satisfy the 400-word floor.
- **Do not reuse an exposed holdout as confirmatory evidence.** The stopping policy already says not to call exposed cases unseen. Make clear that rerunning a revised bundle on all 60 supports a complete retrospective comparison, but does not restore the holdout's prior independence.
- **Inspect some apparent passes if reviewer agreement becomes material.** Second review of failures and disputes catches many problems, but cannot reveal all shared false positives. A small, declared sample of passes is useful; exhaustive double review is unnecessary for an exploratory evaluation.

## Evidence and claim boundaries

The worked examples are original, labeled fixtures. They do not need fabricated public citations. The versioned-limit answer uses supplied labels appropriately, the numerical examples show derivations from supplied values, and the interpretation answer reasons from the quoted passage. No external factual citation in these five files was available to verify, and no external factual gold was inspected.

The protocol correctly distinguishes source-packet reasoning from live retrieval quality, and readability judgments from human comprehension. Keep those boundaries in the release report. Model-judged improvements on these scenarios would be evidence about agent responses under this harness. They would not demonstrate that human readers learned more, that tables improved retention, or that native reference selection works. Conversely, a human-learning study could motivate a writing technique without demonstrating improved agent performance. Neither kind of evidence substitutes for the other.

**Confidence: 0.93** in the example correctness and internal design assessment; **0.84** in the protocol-risk assessment, which depends on how the eventual comparison is described.

**Key caveats:** This is a design review, not a review of case quality, live retrieval, generated answers, gold correctness, operational isolation, or human comprehension. The proposed edits are focused improvements, not evidence that the draft already exhibits these failures in practice.
