# Publication review

Reviewed on November 16, 2026. **Decision: no publication blockers found within this review's scope.**

## Scope and evidence snapshot

Reviewed the README, installation and attribution guides, evaluation guide and advanced report, final outcome and annotation records, the canonical `SKILL.md`, and all three runtime references. Targeted read-only checks covered supporting counts, measurements, runtime hashes, the recorded example, and maintained-documentation links. The exact 34 input files and their inspection depth are recorded in `evals/advanced/reviews/publication-review-inputs.json`.

The evidence input bound to this review is `evals/advanced/reviews/publication-evidence-snapshot.json`, SHA-256 `32020387cd0d677a5484d08ac02fdf70b585878a73559660cb1dbcb8460ee854`. It was byte-identical to `evals/advanced/evidence.json` at the final inspection. Binding the stable snapshot avoids a circular dependency when the final evidence manifest subsequently includes this review. This is a review of the recorded release evidence, not a new model evaluation.

## Findings

- **Versions and denominators agree.** The reviewed evidence contains 225 actual responses across 66 distinct prompts: 66 each for v4, v5, and v7, and 27 for stopped v6. Long-case outcomes are 60/60, 59/60 with one partial, 26/27 with one failure, and 60/60 respectively. V4, v5, and v7 each have six passing short responses; v6 has none generated. The 29 secondary full-answer reviews include nine for v7. These counts agree with `README.md`, `evals/advanced/REPORT.md`, and `evals/advanced/v7-outcome.json`.
- **Measurements are accurately labeled.** Recalculation confirms the 545.1 mean prompt whitespace tokens, approximately 11.3-fold length ratio, 1585-word core, and reference counts of 822, 846, and 944. Reported v7 length changes round correctly to +0.2% word tokens and +1.1% Unicode characters. `evals/advanced/measurement-notes.json` distinguishes the response regex metric from whitespace splitting and linguistic tokenization. The 81 synthetic tests remain separate from actual answers, and the historical archive has 194 response records across 46 cases.
- **Claims preserve the evidence limits.** The maintained documents identify all final v7 results as retrospective, retain the original split labels without implying renewed holdout status, disclose v6's incomplete coverage, and acknowledge that v4 already passed the long suite. They do not assert universal superiority, measured human comprehension, latency or cost improvements, or universal IDE activation. Injected references, batch contexts, imperfect model review, unavailable model/runtime details, and missing historical execution logs are disclosed in `evals/advanced/REPORT.md`.
- **Failures and qualifications remain visible.** V5 B22's partial and conflicting secondary pass, v6 B21's failure, answer-key limitations including A24's literal-key/prompt distinction, and v7 B28's readable formatting defect are represented consistently in the report, `evals/advanced/gold-annotations.json`, and `evals/advanced/residual-observations.json`. No perfection claim is implied by the 12/12 summaries.
- **Runtime and example agree with the records.** The current core and three references match both the frozen v7 hashes and `docs/installation-check-v7-local.json`. The README quotation and `evals/advanced/examples/N04.md` match the raw N04 response after removing presentation-only blockquote prefixes. The runtime remains agent-neutral, with optional guides and no evaluation keys in the four reviewed runtime files.

## Documentation links and installation claims

The separate read-only link audit found **87 local inline link occurrences resolving to existing paths**; the sole local fragment matches its heading. Of **34 distinct external URLs**, 31 returned page content and none was confirmed broken. All 17 official installation-source URLs returned content. The inspected official pages support the stated Node.js requirement, shared skill locations, and VS Code customization command; `docs/installation.md` correctly limits the observed installation result to Linux discovery, layout, and exact bytes.

Three destinations remain **unverified through the retrieval service**, which returned `DisabledError` without a destination HTTP status:

- The [maintainer profile](https://github.com/jamestesting0) in `README.md`.
- The [issues page](https://github.com/jamestesting0/clear-explanations/issues) in `README.md`.
- The [Extended Karpathy Guidelines attribution](https://github.com/jamestesting0/extended-karpathy-guidelines/blob/main/SKILL.md) in `docs/sources.md`.

These retrieval failures do not establish broken links.

## Blockers

None found in the reviewed release snapshot.

## Optional suggestions

Recheck the three undetermined external destinations when direct access is available. No wording correction is required on the evidence currently available. The initially observed collapsed spaces in JSON prose and the report's singular “1 win” grammar were corrected by the release owner and reread before this review was finalized.

## Limits and confidence

The previously successful archive check on 225 responses and 81 synthetic software tests were supplied or recorded results; this reviewer did not rerun those suites. Checks here were targeted documentary and arithmetic checks. No answers were generated or regraded, and no runtime, documentation, raw response, or score was edited by this reviewer. Native host activation, Windows behavior, human comprehension, and historical execution authenticity were not independently tested. Successful external retrieval is a point-in-time observation.

**Confidence: 0.97** for publication consistency within this stated scope. **Key caveats:** model judgments remain fallible; final cases are exposed regressions; three external destinations remain unverified.

## Required corrections

None.
