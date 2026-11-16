# Expanded explanation benchmark: four recorded versions

Recorded on **November 16, 2026**. This is an exploratory evaluation of actual model answers, including two rejected candidates and the revisions prompted by their errors.

## Result and scope

The final v7 bundle passed **60/60 long prompts** and **6/6 known short prompts** under the registered rubric. The archive contains **225 actual responses across 66 distinct prompts**: 60 newly authored long prompts and six known short prompts. V4, v5, and v7 each answered all 66; v6 was stopped after 27 answers exposed a material numerical error.

**All final v7 results are retrospective regression evidence.** Twelve cases were withheld during v5 development and selection, then exposed during review. Reusing those cases for v6 and v7 did not restore unseen status.

| Version | Long answers generated | Pass | Partial | Fail | Mean score | Mean word tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| v4 | 60 | 60 | 0 | 0 | 11.9833/12 | 848.2 |
| v5 | 60 | 59 | 1 | 0 | 11.9667/12 | 798.1 |
| v6 (stopped) | 27 | 26 | 0 | 1 | 11.7778/12 | 769.0 |
| v7 | 60 | 60 | 0 | 0 | 12.0000/12 | 850.1 |

V6 covers a different, incomplete subset, so its averages are **not directly comparable** to the other rows. Its [stop record](v6-stop-record.json) identifies the 27 completed cases and 39 not generated. No missing answer was counted as a pass.

V4 already passed all 60 long cases. V7's answer length changed by **+0.2% in word tokens** and **+1.1% in Unicode characters** relative to v4. These descriptive measurements do not establish better readability, human comprehension, or the best possible explanation.

The [case catalogue](CASES.md) links every recorded answer. [Evidence](evidence.json) contains recomputable aggregates and file bindings; [records](records) preserve answers, metadata, and original primary judgments.

## What was added

The runtime has a **1585-word core** and three optional guides. Agents are told to read only support useful to the current question.

| Resource | Purpose | Whitespace words |
| --- | --- | ---: |
| [Evidence and sources](../../references/evidence-and-sources.md) | Match claims to applicable evidence, preserve uncertainty, resolve conflicts, and cite exact support. | 822 |
| [Explanation patterns](../../references/explanation-patterns.md) | Cover long requests, code state changes, calculations, mechanisms, interpretations, and decisions. | 846 |
| [Worked examples](../../references/worked-examples.md) | Six original examples with explanations of their presentation choices. | 944 |

The examples cover shared versus copied Python objects, counts versus rates, versioned contracts, causal claims, literary interpretation, and a one-sentence definition. These guides are writing aids, not factual authorities for the user's topic. [Sources and attribution](../../docs/sources.md) separates design influences from evidence of model performance.

## Review and revision history

| Stage | Finding and action |
| --- | --- |
| Frozen v4 baseline | Regenerated the previous single-file skill on the same new prompts. |
| Expanded design draft | Added optional guides and six examples. No generated-answer results are claimed for this design-only draft. |
| Design round 1 | Simplified copying terminology, showed numerical calculations, qualified causal and literary claims, and clarified source applicability and absent material. |
| Design round 2 | Found no runtime blocker but identified three verifier gaps. Repaired constraint accounting, exact provenance binding, and summary/short-case coverage. |
| Frozen v5 | Development and validation passed; original-holdout B22 contained an unsupported negative. Retained its primary partial and conflicting secondary pass. |
| V6 revision | Added a negative-claim audit and a contrast between an unreported event and one established not to have occurred. |
| V6 stopped after 27 answers | B22 passed, but B21 propagated a wrong subtotal into cancellations, closing accounts, and retention. Both reviewers failed it. All completed answers remain. |
| V7 revision | Added verification with available, permitted tools; independent reconciliation from original inputs; precision until rounding; and consistency across the answer. |
| Full v7 retest | Generated all 60 long and six short answers with frozen guidance, original batch orders, and separate blind review. No answer was repaired by hand. |

The [first design review](reviews/design-round1.md), [second design review](reviews/design-round2.md), [v6 review](reviews/v6-design-review.md), and [v7 review](reviews/v7-design-review.md) are preserved. Design reviews are separate from reviews of actual answers.

### B22: an unknown became a negative fact

The fictional diary packet does not establish whether anyone inspected the bell mechanism. V5 nevertheless says, **“The diarist did not inspect the North Bell.”** That exceeds the evidence, although its central historical conclusion remains sound.

The primary review assigned **10/12, partial**. A secondary review assigned **12/12, pass** and missed the sentence. A [focused source adjudication](reviews/B22-adjudication.md) confirmed the unsupported negative. Both judgments are retained; the favorable review does not replace the primary partial.

V6 and v7 preserve the difference between “not established” and “did not occur.” They permit definite negatives supported by explicit evidence or complete observation. Compare the unchanged [v5](outputs/v5/B22.md), [v6](outputs/v6/B22.md), and [v7](outputs/v7/B22.md) answers.

### B21: one wrong subtotal contaminated later calculations

V6 listed **45 + 9 + 4** continuing accounts but reported **59**. It then gave six cancellations, 81 closing accounts, and 90.77% retention. The supplied inputs imply **58 continuing accounts, seven cancellations, 80 closing accounts, and 89.23% retention**. Its recurring-revenue reasoning was otherwise correct.

Primary and secondary reviewers both failed it at **7/12**. The run stopped after preserving completed and in-progress answers. V7 asks for multistep arithmetic to be verified with an available, permitted calculation tool and reconciled independently from original inputs. Reusing a wrong subtotal in a second formula is not an independent check. A manual fallback remains available; checking transcripts need not clutter explanations.

The independently reviewed [v7 answer](outputs/v7/B21.md) has the correct values; the failed [v6 answer](outputs/v6/B21.md) remains public. This supports a targeted correction and retest, not a guarantee against future arithmetic errors or proof that the guidance caused every difference.

## Longer prompts with connected difficulties

Two fresh-context agents authored the 60 original synthetic exercises without seeing the candidate skill or earlier response evidence. They contain **460–597 whitespace tokens**, averaging **545.1**, versus **48.1** in the previous 46-case suite—about **11.3 times the mean length**. Length is not a calibrated difficulty score.

| Area | Difficulties exercised |
| --- | --- |
| Code and data | Shared cancellation, exception replacement, mutable views, closures, SQL duplication, window frames, rounding, and misleading deadlock repairs. |
| Distributed systems | Retry identity, crash boundaries, fencing, watermarks, causal state, cleanup, authorization scope, and conflicting parsers. |
| Quantitative reasoning | Correlated evidence, changing denominators, weighted ratios, interactions, repeated testing, missing-data bounds, and resource accounting. |
| Science and causal claims | Mechanism versus measurement, delayed readout, intervention versus selection, interference, material balance, and attribution. |
| Sources and interpretation | Effective dates, overlapping policy scope, dependent testimony, literary interpretation, and translation that cannot prove historical implementation. |
| Reader and language | English, German, Simplified Chinese, Spanish, French, and Portuguese requests, with vocabulary adapted to the stated audience. |

The original split was **36 development + 12 validation + 12 holdout**. Six known short prompts are separate. The table reports passes over answers actually generated in each original split; these labels do not imply unseen status for v7.

| Original split | v4 | v5 | v6, incomplete | v7, retrospective |
| --- | ---: | ---: | ---: | ---: |
| Original development | 36/36 | 36/36 | 15/15 | 36/36 |
| Original validation | 12/12 | 12/12 | Not generated | 12/12 |
| Original holdout | 12/12 | 11/12 | 11/12 | 12/12 |

### Source checks and imperfect answer keys

The [authoring record](AUTHORING.md) preserves fixtures and verification. Author A records 103 individual assertions. Author B records 30 case-level checks: 21 computations/simulations and nine qualitative author reviews. These are different units, separate from generated answers and human-learning measurements.

Known source/key issues remain visible in [gold annotations](gold-annotations.json):

- **A20:** an explicit `ROWS` cumulative frame is not essential under the packet's unique `(ts,id)` ordering; the default `RANGE` frame is equivalent there. The candidate uses `ROWS`, so this key overrestriction does not affect its pass.
- **A23:** a supplied 104% value is impossible on its percentage-of-tickets scale. Answers should flag it and qualify the requested arithmetic. Correct calculations do not validate impossible source data.
- **A24:** two reciprocal rates in the key are illustrative. The prompt requires the relevant sequential-client assumption when using inverse latency; equivalent sufficient reasoning is accepted. The v7 secondary review preserves C7 as partial against the literal key, with an explicit overrestriction flag and an overall pass against the actual prompt. No primary score changed.
- **B22:** a proposed museum caption is optional although criterion C8 can be read as mandatory. This does not excuse the separate inspection claim.
- **B28:** a fixed training count within a team does not alone isolate an own-assignment effect with peers held fixed. Both v6 reviewers accepted the qualified answer; the secondary review enumerated 252 fixed-five assignments to check this issue.

Original prompts, keys, answers, and primary scores remain unchanged. Post-review annotations are marked and were not secretly supplied to earlier reviewers.

## Generation and review method

### Inputs and context

Completed conditions used the original batches and order, fresh-context transport, inherited model configuration, tool policy, and common generation wording. Batches contained four to six cases: contexts were fresh per batch, not per case. Responders were told to read only their frozen packets, without keys, prior answers, feedback, or installed skills.

V4 used single-file guidance. V5, v6, and v7 packets injected the core and all three references. This evaluates supplied content; it does **not** test native selective loading. Ordinary use is designed to load only useful support.

Safe calculations and execution were allowed when appropriate. Exact underlying model identifiers and full surrounding runtime prompts were not exposed and remain null. The [common generation wording](generation-instructions.md) was recorded during the run; it is not a transcript of complete runtime context. Canonical packets and ordered batch hashes preserve the available inputs with those limits stated.

### Independent semantic reviews

Every actual answer received separate model review using its prompt, evidence, key, [protocol](protocol.json), [addendum](protocol-addendum.json), and [review instructions](review-instructions.md). Condition identities and expected winners were withheld. Style may reveal conditions, so blinding is imperfect.

The six dimensions are **accuracy, evidence, coverage, clarity, structure, and fit**, each 0–2. Passing requires **at least 11/12**, all essential requirements of the actual prompt, explicit constraints, and no critical error. The gold operationalizes those requirements but remains open to documented correction; the A24 clarification above preserves the literal-key status and the prompt-based judgment separately. A material central error, invented evidence, essential omission, or hard constraint violation fails regardless of total. A local noncritical imprecision can produce partial, as v5 B22 did.

Reviewers checked meaning rather than keywords and could execute calculations or fixtures. V4/v5 jobs usually paired anonymous answers for four to six cases. V6/v7 used four to six individual answers per review job, as disclosed in the [v6 review plan](v6-review-plan.json) and [v7 retest plan](v7-retest-plan.json). That workload difference limits direct comparison.

There are **29 secondary full-answer reviews**, plus the focused B22 adjudication. These are additional judgments, not generated answers. Audits cover the first passing case in each represented original hard split, material failures/disputes, and B21/B22 revisions. Secondary scores never silently replace primary scores. V6 A09 received primary 11/12 for a local citation weakness and secondary 12/12; both passed and the primary score remains.

### Freeze and exposure

The [seal registration](seal-registration.json) preceded B19–B30 disclosure. The [v5 freeze](release-freeze.json) preceded the [reveal](holdout-reveal.json), with matching sealed hashes. The skill author did not inspect those cases during v5 development or selection; their fixture author and construction tools necessarily had access.

The [v6 plan](v6-retest-plan.json), [freeze](v6-release-freeze.json), and [stop record](v6-stop-record.json) document its revision and rejection. The [v7 plan](v7-retest-plan.json) and [freeze](v7-release-freeze.json) preceded the full rerun. **Every final v7 prompt was already exposed.** A future generalization claim needs new unseen prompts.

## Detailed outcomes

| Mean score on all 60 long cases | v4 | v5 | v7 |
| --- | ---: | ---: | ---: |
| Accuracy | 1.9833 | 1.9833 | 2.0000 |
| Evidence | 2.0000 | 1.9833 | 2.0000 |
| Coverage | 2.0000 | 2.0000 | 2.0000 |
| Clarity | 2.0000 | 2.0000 | 2.0000 |
| Structure | 2.0000 | 2.0000 | 2.0000 |
| Fit | 2.0000 | 2.0000 | 2.0000 |

The v7-versus-v4 verdict comparison records **0 wins, 60 ties, and 0 regressions**. The score comparison records **1 win, 59 ties, and 0 regressions**. Critical failures for v4/v5/v6/v7 are **0/0/1/0**, respectively; v6 covers only 27 cases.

V4 A19 contains a local ordering imprecision: the latch ensures both first-lock arrivals before second-lock attempts, but does not force A to arrive before B. Both original review rounds retained its correct central deadlock analysis and assigned 11/12, pass. Its wording, v5 B22's partial, and v6 B21's failure are preserved.

V7 B28 retains a minor formatting defect: its opening arithmetic has literal TeX-style escapes without matching math delimiters. The secondary reviewer explicitly noted it, found the numerical meaning clear, and retained 12/12, pass. The [residual observation](residual-observations.json) and raw answer remain unchanged. A rubric pass does not mean every response is typographically flawless.

### Short-question regression check

| Version | Passes | Mean word tokens | Mean Unicode characters |
| --- | ---: | ---: | ---: |
| v4 | 6/6 | 167.2 | 1091.3 |
| v5 | 6/6 | 170.0 | 1072.7 |
| v7 | 6/6 | 157.8 | 1001.2 |

V6 stopped before short answers were generated. These six known prompts check the concrete risk of extra guides inflating ordinary answers; they are not new unseen tasks. [N04](examples/N04.md) is an unedited v7 short response.

**Counting convention:** prompt/runtime lengths use whitespace splitting. Response `word_count` and `mean_words` use the unchanged Unicode word-token regex in the harness, including code and numbers; it is not a linguistic Chinese tokenizer. Character counts use Unicode code points. [Measurement notes](measurement-notes.json) record this distinction; no score or numerical measurement changed. Neither count measures comprehension. No latency or token-cost benchmark was performed.

## Integrity and replay

From the repository root with Python 3.10+:

```sh
python evals/advanced/check.py --require-current
python evals/advanced/check.py --json
```

The verifier reconstructs packets and checks runtime resources, case/key/review bindings, batches, response hashes, coverage, constraints, score arithmetic, outcomes, and split/paired summaries. Hard failures override reporting outcomes without erasing original judgments. Passing establishes internal consistency, not correctness of a model review.

Restore an archived runtime into a new directory and prepare replay packets:

```sh
python evals/advanced/materialize.py --variant v7 --out evals/runs/frozen-v7
python evals/tools/evaluate.py packets --cases evals/advanced/cases.json --out evals/runs/replay-v7 --bundle replay=evals/runs/frozen-v7
```

Historical entry files use `INSTRUCTIONS.md` to avoid discovery as active skills. Materialization restores `SKILL.md` without changing bytes; preparing packets does not generate answers. The [evaluation guide](../README.md) covers adapters, collection, blind review, and reports.

The [software check record](software-checks.json) reports **81 synthetic tests**: 38 core/transport, four Codex-adapter, 27 archive-checker, and 12 replay-helper. The [helper audit](reviews/replay-helper-audit.md) documents bounded checks. These are separate from 225 actual answers. The earlier [194-response, 46-case archive](../REPORT.md) remains independent.

## Limits and release judgment

- **Model review:** scores come from models, with no human comprehension or satisfaction study. B22 demonstrates a real missed error and disagreement.
- **Synthetic, exposed prompts:** cases are designed exercises, not a random sample of real work. Keys are fallible; final results are retrospective.
- **Supplied sources:** this tests reasoning inside packets, not live retrieval quality or navigation through an unfamiliar repository.
- **Runtime uncertainty:** exact model IDs and complete surrounding prompts were unavailable; cases shared batch contexts. Cross-model or cross-agent performance is not established.
- **Injected references:** the benchmark supplies every guide. Installer checks establish discovery, layout, and bytes, not activation or selective loading in every IDE. See [installation scope](../../docs/installation.md).
- **Execution history:** reviewers reproduced many calculations, but complete historical tool-call logs are not archived. Reproduction does not authenticate earlier execution claims.
- **Near-ceiling baseline:** v4 already passed the long suite. Nonrandom sampling, workload differences, and one response per condition prevent a broad superiority claim.
- **Archive trust:** hashes bind declared files internally; they do not prove instruction compliance or provide an external timestamp authority.

V7 is selected because its complete recorded rerun satisfies this rubric and rechecks both observed failure cases independently. That is a bounded release decision, not a guarantee of perfect explanations. Future work should retain these regressions and add new cases or human comprehension checks.
