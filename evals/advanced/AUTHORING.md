# Advanced benchmark authoring and source verification

All 60 benchmark cases are **original synthetic material**, according to the recorded authoring provenance. This archive documents their construction and the checks of their supplied source material. Model-response evaluation and human-comprehension measurement are separate evidence categories.

The evidence below comes from the [A authoring report](source-verification-a.json) and the [B open authoring report](source-verification-b-open.json). Each export includes the SHA-256 of its original, unmodified verification file, the hashes of the preserved source files, and aggregate statistics from the original authoring audit or manifest.

## Inventory and prompt length

| Authoring batch | Cases | Development | Validation | Sealed holdout | Recorded words per prompt | Total recorded words |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 30 | 24 | 6 | 0 | 460–591 | 16,117 |
| B | 30 | 12 | 6 | 12 | 511–597 | 16,589 |
| Combined | **60** | **36** | **12** | **12** | **460–597** | **32,706** |

These are recorded whitespace word counts, not model-token counts or a language-independent measure of reading difficulty. B explicitly records Python `str.split` as its counting method. The combined totals and range were checked by arithmetic over A's audit and B's manifest aggregates. B's open subset contains 18 cases and 9,836 words; the manifest records 12 sealed cases and 6,753 words. No sealed prompt, rubric, builder, or verification file was opened while preparing the initial open authoring archive. The holdout figures above come only from the pre-existing aggregate manifest. See `publication_provenance.aggregate_statistics` in the two exported reports for the source values.

## Preserved source files

| Location | Contents and purpose |
| --- | --- |
| [fixtures/a/build_cases.py](fixtures/a/build_cases.py) | Original A authoring and verification builder, preserved byte for byte. |
| [fixtures/a/](fixtures/a/) | Ten original Python, JavaScript, and Java fixture programs, including the separate A19 repair fixture. |
| [fixtures/b/build_open.py](fixtures/b/build_open.py) | Original builder for B's 18 open cases, preserved byte for byte. |
| [fixtures/b/verify_open.py](fixtures/b/verify_open.py) | Original verification script for B's open cases, preserved byte for byte. |
| [source-verification-a.json](source-verification-a.json) | Original A outcomes and runtime versions, with command paths normalized for this repository and publication provenance added. |
| [source-verification-b-open.json](source-verification-b-open.json) | Original B open verification records, with publication provenance added. |

The fixture directories contain executable source files only. Generated case and rubric JSON files are not duplicated there. B's archived builders and verification script are explicitly the open versions. Separate sealed-material publication is governed by the release-freeze protocol.

The source files retain their original bytes, including any author-environment paths embedded in builders. The normalized command paths in the verification export do not rewrite those builders. Builders construct artifacts and may write files; reconstruction should use a disposable working copy with the expected paths. This publication step copied and checked source bytes; it did not execute the builders or rerun the fixture suites.

## What the recorded checks establish

### Batch A: executed source checks

The [original A report](source-verification-a.json) records **103 checks, all marked passed**, across 30 cases:

| Recorded method | Cases |
| --- | ---: |
| Executed fixture program | 9 |
| Executed SQLite query | 3 |
| Executed calculation or simulation | 18 |

The nine fixture-program cases use ten archived programs because A19 also records a separate repair execution. The report preserves their outputs, exit codes, check labels, actual and expected values, tolerances, fixture hashes, and the additional A19 repair record.

These checks support specific control-flow traces, query results, calculations, and simulations in the recorded environment. They compare those results with author-supplied expectations. They do not independently establish the correctness of every source assumption, the plausibility of every input, the completeness of a rubric, or the quality of an explanation. In particular, the known A23 defect below coexists with passing arithmetic checks.

The original report records Python **3.12.14**, SQLite **3.53.1**, Node.js **v24.22.1**, and OpenJDK **21.0.13**. The full Java runtime string remains in the JSON. These identify the original execution environment; this archive does not assert that the checks were repeated under other versions.

### Batch B open: computed checks and qualitative author reviews

The [B open report](source-verification-b-open.json) contains **18 case-level verification records**. Twelve record computations or operations such as date comparisons, accounting reconciliations, energy balances, branch behavior, enumeration, and JSON parsing. Six—B01, B02, B05, B09, B12, and B17—are labelled `manual source-and-rubric consistency review`, with the status `reviewed during original authoring`.

Those six qualitative reviews consider whether supplied proposals were promoted to facts, missing facts were filled in, rubric requirements were substantive, and outside sourcing was necessary. They are author reviews, with no recorded independent model-response evaluation. The word “manual” in their original labels does not establish that a human comprehension study or independent human adjudication occurred.

B's top-level `status: passed` is preserved with that scope. Its 18 records are not a uniform assertion count comparable to A's 103 checks. The B report does not record interpreter/library versions, command lines, stdout, or exit codes in the form used by A. The archived open scripts and their hashes provide implementation provenance; the report's limits remain material when assessing reproducibility and strength of evidence.

## Known A23 source defect

The original A23 packet contains a **104% value that is impossible on its stated percentage scale**. This is a known source defect. The raw authoring source is preserved, so the value has not been silently repaired in this archive.

A23's recorded checks cover a difference-in-differences value, a pretrend differential, and a descriptive trend adjustment. Their passing results establish the recorded arithmetic against the original expectations; they do not establish that the source percentages are valid. Any interpretation of response performance on A23 must retain this qualification. A corrected packet would need a distinct fixture version and appropriately scoped evaluation evidence.

## Original primary reference

A records one external primary reference: the [Oracle Java SE 21 `List` API specification](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/List.html), with a recorded consultation date of **2026-11-16**, for A03. The authoring record uses it for the distinction between an unmodifiable list and mutable elements, and for the limits of a sublist view after structural changes to its backing list. The original URL, publisher, date, paraphrase, and case association are retained under `primary_sources` in the A export.

B records that no outside research was performed because its source identifiers refer to supplied synthetic packets. Synthetic case provenance and an external reference for Java API behavior are compatible: the reference documents behavior used by an original fixture.

## Export normalization and integrity

The original raw verification file hashes are:

| Original report | SHA-256 of original bytes |
| --- | --- |
| A `verification.json` | `0c73bd88d54d48ecaf10961bc7060f32e60dba99ed6f49b24efb5389049d8353` |
| B open `verification.json` | `24a52417562bb94ebc011ddf14688f5408cfc77d350de9d4f1df0686d2766675` |

For A, 15 command arguments were normalized: five environment-specific Python executable paths became `python3`, and ten absolute fixture paths became repository-relative paths under `evals/advanced/fixtures/a/`. Commands in the export assume the repository root as the working directory. Existing generic `node` and `java` command names were retained. The exact modified JSON pointers are listed in `publication_provenance.normalized_json_pointers`.

No original B fields needed path or interpreter normalization. Both exports add `publication_provenance`, which records the original verification hash, normalization note, preserved source-file hashes, and aggregate-source hash and statistics. Original outputs, results, check outcomes, versions where recorded, and source-reference data are preserved. Original relative names in `file_sha256` retain their meaning within the authoring report; they do not imply additional copies in the fixture directories. The exports are newly serialized JSON, so their own file hashes differ from the original raw verification hashes above.

## Evidence units and limits

| Quantity | Unit and scope |
| --- | --- |
| 60 | Authored synthetic benchmark cases across all splits. |
| 103 | A source-fixture assertions recorded as passed. |
| 18 | B open case-level verification records, including six qualitative author reviews. |
| Actual generated model outputs | Count separately from response-run manifests; no such count is established by this authoring archive. |
| Blinded grading or human comprehension | Requires separate evaluation evidence; no outcome is established by these authoring records. |

Source checks can catch concrete mistakes in expected computations and traces. Qualitative author reviews can identify consistency problems that are not encoded as executable assertions. Neither is an independent test of how well a model explains the material to a reader. The known A23 defect is a concrete reason to keep source validity, computation checks, response grading, and human comprehension distinct.

## Holdout publication after release freeze

The [release freeze](release-freeze.json) was written before the skill author opened B19–B30. The [reveal record](holdout-reveal.json) binds that freeze and confirms that all three sealed file hashes matched the earlier [seal registration](seal-registration.json).

The [B holdout verification report](source-verification-b-holdout.json) is now published with the original [builder](fixtures/b/build_sealed.py) and [verification program](fixtures/b/verify_sealed.py). The programs retain their original bytes. The report preserves every original field and adds publication provenance; this export did not rerun the source calculations.

Its 12 case-level records comprise nine computations or simulations and three qualitative author reviews (B22, B23, B27). The computed records cover decay, scope/date aggregation, cohort accounting, material balance, resource scheduling, transfers versus resource costs, assignment arithmetic, retry behavior, and bounds from incomplete margins. The qualitative records concern source scope and alternative readings. As with the open batch, these are source checks and author reviews, not independent explanation-quality scores or human-learning measurements.

Across both B subsets, there are **30 case-level source-verification records: 21 computed and nine qualitative**. This count remains distinct from A's 103 individual assertions, the harness's synthetic tests, and the generated-answer count. The source verification report's original hash is `e4065899b1521b457db67ef95057d65e4e65780b9ab18bace543c08542ed901c`.
