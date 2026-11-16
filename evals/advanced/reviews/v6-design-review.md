# v6 independent design review

## Decision

**Pass the design review. No material blocker or required wording change was found.** The revision directly addresses the abstract failure described in the retest plan: treating an unreported event as an event established not to have occurred. The wording supports both honest uncertainty and definite negative claims when the evidence warrants them.

**Overall confidence: 0.94.** This is confidence in the design assessment, not a prediction of a measured pass rate.

## Scope and evidence

Reviewed the four runtime files under `explain-advanced-runtime/v6-draft` and compared each only with its counterpart under `explain-advanced-runtime/v5`: `SKILL.md`, `references/evidence-and-sources.md`, `references/explanation-patterns.md`, and `references/worked-examples.md`. Also read `clear-explanations/evals/advanced/v6-retest-plan.json` for the abstract failure description and planned retest.

No cases, rubrics, raw model answers, scores, variant maps, or other review files were inspected. No runtime files were edited, no model answers were generated, and nothing was published.

The comparison shows two additions: one bullet in `SKILL.md` under “Check before sending,” and one section, “Check negative claims explicitly,” in `references/evidence-and-sources.md`. The explanation-patterns and worked-examples references are unchanged.

## Findings

| Criterion | Assessment | Confidence |
| --- | --- | --- |
| Distinguishes an unreported event from established absence | Sufficient and correctly scoped | 0.98 |
| Remains portable | No new environment or tool dependency | 0.97 |
| Avoids overcautious or repetitive explanations | Appropriate safeguards; confirm behavior in retest | 0.90 |
| Generalizes beyond the illustrative example | General principle with one compact contrast | 0.94 |

### 1. The evidence distinction is correct

The new core bullet explicitly separates events left “unreported or unknown” from claims that an event did not occur. Its alternative bases for a definite negative—explicit support or a complete observation that rules out the event—avoid imposing a blanket ban on negative conclusions. This is more operational than v5's existing general warning against converting absence of evidence into evidence of absence. [Source: v6 `SKILL.md`, “Check before sending”; v5 and v6 `references/evidence-and-sources.md`, “Make support visible without clutter.”]

The new table makes the boundary concrete. A summary reporting that tests A and B passed supports uncertainty about whether C ran. An explicit statement that C was not run supports the scoped conclusion “in that recorded run.” That scope matters: the example does not convert a statement about one run into a claim about every run. [Source: v6 `references/evidence-and-sources.md`, “Check negative claims explicitly.”]

The accompanying logging rule also covers valid inference from missing records. It permits that inference when the log's coverage and recording behavior warrant it. Thus the revision handles both an explicit recorded absence and an absence inferred from a sufficiently complete observation. No further distinction is required for this small revision.

### 2. The revision remains portable and general

The core rule concerns evidence and events generally. It introduces no required tool, service, platform, external citation scheme, or output format. The evidence reference continues to use the existing relative-file structure. The run-log example is illustrative; the operative rule applies to omissions in other records and summaries as well. [Sources: v6 `SKILL.md`, “Load only useful support” and “Check before sending”; v6 `references/evidence-and-sources.md`, “Check negative claims explicitly.”]

The examples use generic A/B/C labels. The new text contains no evaluation identifiers or instructions tied to the retest suite. The broader checks for “no,” “never,” “did not,” and “only” make the revision applicable to categorical exclusions beyond the particular example. Including side notes and table cells addresses where an unsupported exclusion can appear without prescribing additional sections in the answer.

### 3. The wording does not require repetitive uncertainty

The core audit sits within a **silent** final check. The evidence reference tells the writer to keep checking work behind the answer. The revision therefore asks for better claim calibration, not a visible checklist or a disclaimer attached to every statement. Existing guidance still favors one precise limitation, the shortest complete explanation, and removal of repetition. [Sources: v6 `SKILL.md`, sections 1, 3, and 6; v6 `references/evidence-and-sources.md`, opening and “Make support visible without clutter.”]

“Otherwise name what remains unknown” should be read in the context of the negative claim under consideration. It does not require cataloguing unrelated missing facts. The two-row contrast also supplies a clear definite answer when absence is established, which helps prevent the rule from becoming indiscriminate hedging.

The short reminder in the core file and the fuller contrast in the selectively loaded reference serve different purposes. Their overlap is proportionate and does not warrant consolidation.

## Retest implications and caveats

The plan appropriately calls for freezing the reviewed revision before generation and treating results on the exposed original suite as retrospective regression evidence. This design review does not establish that the model will consistently apply the new rule or that any observed failure has been resolved. The plan's pending second review and subsequent answer-level assessment remain separate sources of evidence. [Source: `v6-retest-plan.json`, `planned_retest`, `holdout_status`, and `review`.]

Within the planned review, the useful behavioral question is whether unsupported negative claims become accurately bounded statements while supported negatives remain direct. A new tendency to repeat unknowns or weaken explicitly supported conclusions would be a regression, but the current wording does not itself create a material design defect.

**Optional polish:** None is needed before freezing. Additional examples or audit language would increase the size of the intervention without resolving an identified wording problem.

**Key caveats:** This was a bounded static comparison, not an empirical evaluation. It did not inspect the original failure or any response output, so it cannot certify remediation or unseen-case generalization. Within that scope, the revision is sufficient to proceed to the planned retest.
