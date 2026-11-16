# V7 focused design review

## Decision

**No required changes.** The v7 draft directly addresses the abstract failure described in the retest plan: an incorrect multi-row count being carried into derived totals. It requires a calculator or code check for multi-step arithmetic, then asks for reconciliation from original inputs rather than accepting agreement between calculations that share the same derived subtotal. The manual fallback, evidence limits, and compact-answer guidance remain coherent.

**Overall confidence: 0.96.** This is a review of the instruction design, not evidence that a model will follow it reliably. The planned retest is still needed to establish observed behavior.

## Scope and evidence

Reviewed only `SKILL.md` and the three reference files in `explain-advanced-runtime/v7-draft`, compared with the same four files in `explain-advanced-runtime/v6`, plus `clear-explanations/evals/advanced/v7-retest-plan.json` for the abstract failure and intended revision. No cases, rubrics, generated answers, scores, variant maps, or other reviews were inspected.

The diff contains one added bullet in `SKILL.md`, section 3, and two added paragraphs in `references/explanation-patterns.md`, under “Quantities, formulas, and research.” `references/evidence-and-sources.md` and `references/worked-examples.md` are unchanged. No runtime files were edited, and no generation or publication was performed.

## Findings

| Requirement | Assessment and supporting instruction | Confidence |
| --- | --- | --- |
| Useful tool checks when tools can be used | Satisfied. The core rule explicitly requires an available calculator or code tool for multi-step arithmetic or totals across rows. The reference covers several categories and linked calculations, requires checking before drafting the quantitative conclusion, and preserves full precision until display rounding. This makes tool checking a requirement in the relevant class of problems. | 0.97 |
| Sensible fallback without tools | Satisfied. The core requires explicit arithmetic and disclosure of unresolved uncertainty when tools are unavailable. The reference more broadly covers tools that “cannot be used” and asks for the decisive arithmetic and an explicit check. This permits a useful answer without pretending a tool ran or making all manual calculation inherently uncertain. | 0.97 |
| Independent reconciliation from source inputs | Satisfied. The core names original inputs and rejects reuse of a derived number as an independent check. The reference adds component sums, opening count plus additions minus removals, and independent derivation of components and changes from the source. Its explicit rejection of a second formula that reuses an incorrect subtotal addresses the intended propagation failure. | 0.98 |
| Honest claims about execution and verification | Satisfied. The new reference expressly prohibits claiming execution or verification that did not occur. This agrees with the existing distinction between source inspection and execution evidence in core section 2, and with the unchanged evidence reference’s prohibition on invented test runs or measurements. | 0.99 |
| Compact ordinary explanations | Satisfied. The tool requirement is scoped to multi-step arithmetic or multi-row totals. The reference says the reader usually needs the decisive calculation rather than the checking transcript. Existing length defaults, relevance-based reference loading, and the final compression pass remain intact. The change adds checking work without requiring a visible checklist or a long answer. | 0.97 |
| Preserve negative-claim safeguards | Satisfied. The categorical-negative audit in core section 6 and the dedicated negative-claims section in the evidence reference remain unchanged. Nothing in the quantitative additions weakens them. | 0.99 |
| Conflicts and duplication | No material conflict or unnecessary duplication found. The core supplies a standalone rule; the selectively loaded reference explains precision, independent derivation, source conflicts, and presentation. Those extra details serve distinct purposes. The instruction to expose disagreeing source values also prevents reconciliation from becoming a demand to force agreement. | 0.96 |

## Optional polish

**Low priority; not a blocker:** align the core bullet’s tool-availability wording with the reference’s broader fallback. For example, “use an available and permitted calculator or code tool” and “If tools are unavailable or cannot be used…” would make the allowance for an explicit no-tool constraint visible in the core alone.

The existing reference already says “If tools cannot be used,” and higher-priority tool restrictions continue to govern. This is a clarity improvement, not a missing safeguard requiring revision before the planned retest.

## Key caveats

- Instruction coverage does not establish successful execution. Whether the model actually checks arithmetic and maintains consistent values across its answer must be evaluated in the authorized retest.
- Independent calculations can still agree when they share a misread source input. The existing source-inspection rule and the new requirement to derive components and changes independently provide appropriate design coverage, but do not guarantee correct extraction.
- The reconciliation examples describe totals and count changes. They should be applied where those quantities exist, without inventing missing inputs or forcing conflicting sources to agree; the surrounding instructions already support that reading.

**Required changes: none.**
