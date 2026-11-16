# Expanded explanation skill: independent design review, round 2

## Decision

**The v5 runtime guidance has no blocking defect in this review. The archive checker needs three bounded integrity/reporting fixes before its success message can support the registered release claims.** These changes concern verification of recorded evidence; they do not require additional explanation templates or another rewrite of the runtime guide.

**Confidence:** 0.97 overall; 0.96 for the runtime assessment and 0.99 for the demonstrated checker gaps. This is a design and code review, not a judgment of the uninspected benchmark answers.

## Scope and method

I read only the permitted v5 `SKILL.md` and its three direct Markdown references, `advanced/protocol.json`, `advanced/protocol-addendum.json`, `advanced/check.py`, and the two permitted interface files, `evals/tools/core.py` and `review_packets.py`. I did not inspect case-authoring directories, benchmark cases, response outputs, variant maps, or a sealed holdout. I did not run the checker against the real archive, generate model responses, or publish anything.

I also executed the current checker against fresh, explicitly synthetic data held entirely in memory. The fixtures used 60 invented hard-case identities, six invented short-case identities, constant illustrative response strings, and mocked bundle/file reads. They did not read benchmark material or write test files. These probes test validator behavior, not explanation quality. The missing real `evidence.json` is expected at this stage and is not a finding.

## Runtime assessment

### Correctness, clarity, and scope

The core guidance provides a coherent order: answer the actual question, inspect the relevant evidence, preserve the necessary causal links, explain vocabulary in context, choose proportionate structure, and check the result. Its length defaults are explicitly subordinate to the user's request and completeness. The instruction to read enough relevant source, without imposing an arbitrary line limit, avoids a common failure in code explanations. It also distinguishes observed execution from a source reading and inferred intent.

The reference-loading table is useful without making every question pay the full cost of the expanded bundle. Relative resource links, a fallback when a reference is unavailable, and host-neutral citation guidance make the text portable. None of the instructions depends on a particular model, external service, repository layout beyond the direct references, or an installed helper tool.

**Assessment: acceptable; confidence 0.96.** No runtime edit is necessary to proceed with evaluation.

### Source discipline

The evidence reference correctly distinguishes applicable authority from mere recency, original study findings from claims about a research literature, supplied evidence from retrieval, and interpretation from established fact. Treating quoted source instructions as material to analyze is also appropriate. Fictional fixtures are labeled; writing references are explicitly denied authority over the user's subject matter.

The guidance preserves genuine disagreements and asks for the missing fact only when it changes the answer. It also allows useful conditional explanations. This is a suitable balance between unsupported certainty and excessive refusal.

**Assessment: acceptable; confidence 0.97.** One optional wording improvement is to replace “closed-source explanation” in `evidence-and-sources.md` with “explanation restricted to the supplied material.” “Closed-source” already has a common software meaning. This is polish, not a blocker.

### Worked examples and overformatting risk

The Python example correctly distinguishes another name for the same list from an outer-list copy, and its printed result is correct. The workshop example correctly separates a 25% decrease in damaged-item count from a 50% relative decrease in the damage rate, with a three-percentage-point absolute change. The versioned-contract example does not invent rejection or truncation behavior. The cache example correctly rejects a causal conclusion from the two measurements. The literary example presents an interpretation as a reading, and the final one-sentence example demonstrates stopping when complete.

The examples show both tables and prose; they do not impose tables on interpretation or direct definitions. The main guide repeatedly makes examples, headings, analogies, and diagrams conditional. I found no reason to add another template.

The remaining risk is empirical: injecting all reference content may still increase answer length or imitation of example formatting. The protocol already acknowledges that injected packets do not test native selective loading, and the addendum's six short transfer cases are the appropriate planned check. The text alone cannot establish the size of that effect.

**Assessment: examples are sound; confidence 0.98. Overformatting remains an evaluation question, not a demonstrated runtime defect.**

## What the archive checker already gets right

`check.py` does not invoke a model or assign new semantic scores. It verifies recorded score arithmetic, score ranges, critical-error overrides, response hashes, byte and word counts, case hashes, and declared response/review identity. It allows semantic failures to remain in an otherwise intact archive. Its success message explicitly says that the exit status concerns integrity rather than universal explanation quality.

The runtime version checks are also meaningful: `read_runtime_bundle` selects the allowed runtime files, rejects symlinks and problematic names, and the bundle digest binds resource names, byte lengths, and exact content hashes. Each response's declared skill and bundle hashes are compared with the frozen variant. `--require-current` compares the full current runtime resource dictionary with the historical release, so changed or added reference content cannot hide behind an unchanged `SKILL.md`.

The concerns below are about gaps between those useful checks and the broader claim that the archived inputs, reviews, and descriptive results have been verified.

## Blocking fixes before the archive is presented as verified

### 1. Preserve hard constraint failures in verdict accounting

**Location:** `check.py`, `stats()` and the constraint/pass checks in `verify()`.

`stats()` counts passes using `fully_reviewed_pass`, but counts partials and failures using the original review verdict. `verify()` allows a hard mechanical constraint failure alongside a passing review if the recorded flags are `deterministic_pass=False` and `fully_reviewed_pass=False`. The review can still assert `hard_constraints_satisfied=True`. No reconciliation is required.

**Demonstrated result:** a synthetic 60-response variant with one response above an explicit hard word limit was accepted with `responses=60`, `pass=59`, `partial=0`, `fail=0`, and `critical_failures=0`. One response disappears from the three verdict counts. This conflicts with the registered policy that an explicit constraint violation is a failure.

**Precise fix:** preserve the original reviewer judgment, but require a resolved, mechanically consistent reporting outcome before accepting the archive. The smallest implementation is to reject the inconsistent record until its review/adjudication identifies the known hard constraint failure. Alternatively, explicitly derive and validate a reporting verdict while retaining the original review. In either approach:

- A proven hard constraint failure must appear in the failure accounting.
- A recorded `hard_constraints_satisfied=False` must not be accepted as a partial or pass under the registered policy.
- Enforce that pass, partial, and fail counts partition the reported response denominator.
- Include hard constraint failures in the critical-failure measure if that field retains the protocol's stated meaning.

These are consistency checks on an explicit rule, not new semantic grading. Do not turn heuristic sentence counts or other `passed=None` checks into hard failures.

**Severity: release blocker. Confidence: 0.99.**

### 2. Validate required provenance and its links, not only declared hashes

**Location:** `check.py`, the recorded-file loop, `source_metadata` checks, and review/version checks; compare the existing interfaces in `core.py` and `review_packets.py`.

The recorded hash inventory can be empty, and neither record files nor the protocol/addendum are required to appear in it. Response metadata is checked against the frozen skill/bundle, but the canonical replay-prompt hash, runtime prompt/batch hashes, guidance mode, and actual ordered batch descriptor are not validated. A batch only needs a size between one and six, the same list length, and membership of the current case. Repeated case IDs within that list are accepted.

Similarly, `review_state == "valid"` is accepted as a stored assertion. The checker does verify the review's response hash and identity, but does not reconstruct its binding to the exact reviewed prompt, gold/rubric file, and review protocol. The arbitrary nonempty list of passing criteria is not evidence that the review was performed against the registered essentials. The addendum explicitly promises these input and provenance bindings.

**Demonstrated result:** the in-memory checker accepted records with no recorded-file hash inventory, no prompt/gold/protocol provenance, and only an unnamed passing criterion. It also accepted `batch_order=[case_id, case_id]` with `batch_size=2` for every response.

**Precise fix:** define the required archive inventory and validate the existing provenance fields against it:

- Require the files actually consumed by the archive, including record files, case snapshots, protocol/addendum, and applicable generation/review provenance, to be covered by the recorded digest inventory.
- Validate each response against its archived canonical packet and ordered batch descriptor. Check distinct case identities, packet hashes, guidance identity/mode, and consistent membership/order across members of the same batch. Verify matched baseline/candidate batch order where the addendum requires it.
- Carry through and validate the exact reviewed prompt/case, response, and gold/rubric bindings already available from the review-packet workflow; verify protocol/addendum provenance as promised. Review validity should follow from those comparisons, not solely from the stored state string.
- Use the gold format's existing criterion identities where available to check structural review coverage. Do not enforce particular answer wording or claim that checking IDs proves a reviewer judged the answer correctly.
- Apply the existing archive containment rule to record-file and frozen-variant paths as well as to hash-inventory entries. A self-contained archive should not silently depend on files outside its boundary.

This need not establish that a model actually followed its instructions or that a reviewer was correct. It should establish which exact inputs and judgments the archive declares and that those declarations agree. Hashes also cannot authenticate a maliciously rewritten archive in which both the evidence manifest and all payloads are changed together; that is a separate trust boundary.

**Severity: release blocker for the promised provenance/version-binding claims. Confidence: 0.98.**

### 3. Require the registered reporting and short-transfer coverage

**Location:** `check.py`, the summaries loop and final coverage checks.

The checker verifies only summary entries that happen to be present. An empty `summaries` object is accepted, so the CLI can claim successful verification without printing any pass/partial/fail counts. It also loads `short-cases.json` but does not require the six registered identities or any release responses to them. The 60-case baseline/release coverage checks do not close that gap.

**Demonstrated result:** `summaries={}` passed verification. A fixture containing six short-case definitions and no short-case response records also passed.

**Precise fix:** require summaries for the compared baseline and release, and define the required coverage for any additional variant being reported. Require the registered `N01`–`N06` transfer identities and completed, bound reviews for the final candidate's six short responses; validate any baseline transfer comparison that is claimed. Keep those six responses separate from the 60 hard cases.

The addendum also calls for descriptive results by split, dimension scores, and paired wins/ties/regressions. Recompute the fields that the checker labels verified, or clearly limit its verified output to the subset it actually checks and validate the additional published aggregates in the archive export. Extra unchecked summary fields should not acquire apparent verification merely because `--json` prints them beside checked fields.

**Severity: release blocker for a completed release archive. Confidence: 0.99.** The archive has not yet been assembled, so this is a missing validation gate, not a claim that the planned report or short transfer work was omitted.

## Verification boundary and key caveats

This review supports retaining the runtime text and repairing the identified checker gates. It does not establish improved model performance, correct benchmark gold, successful blinded review, actual completion of the registered experiments, or native resource-loading behavior. Those conclusions require the later evidence and were deliberately outside this review's access boundary.

The demonstrated checker gaps came from synthetic in-memory executions of the current code. The real archive schema and contents may supply additional evidence, but the current checker does not require or validate the missing links described above. Once those gates are added, a small set of targeted synthetic acceptance/rejection probes is sufficient to check the fixes; no additional model generation is needed for these integrity changes.
