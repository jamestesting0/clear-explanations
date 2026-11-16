# Evaluation report

**Release:** v4 · **Recorded:** 2026-11-16

The final skill passed the project's review standard on **46/46 scenarios**. Development and comparisons produced **194 actual responses**. These counts describe the recorded experiment, not a guarantee about future answers.

## Coverage

| Area | Examples |
| --- | --- |
| Code behavior | Shared list references, early returns, binary search, event-loop order, SQL join multiplication, JavaScript defaults |
| Quantitative reasoning | Entropy, base rates, derivatives, confidence intervals, percentage-point changes, average speed |
| Science | Boiling and evaporation, density, force pairs, climate, photosynthesis |
| Concepts and decisions | Dependency injection, OAuth versus JWT, opportunity cost, centralization, feedback |
| Adaptation | Beginner and expert audiences, Chinese and German, missing source material, requests to explain again |
| Exact constraints | One-sentence answers, required or forbidden tables, CSV-only and code-only outputs |

The complete prompts are in [cases.json](cases.json). Criteria were separate from the answering agents' inputs.

## Reviews and revisions

Two independent design reviews examined the written instructions. Separate agents reviewed actual responses, including anonymized comparisons.

| Draft | Response scope | Pass | Partial | Fail |
| --- | --- | ---: | ---: | ---: |
| v1 | 24 development cases | 24 | 0 | 0 |
| v2 | 36 core cases and 6 natural prompts | 42 | 0 | 0 |
| v3 | All 46 cases | 44 | 2 | 0 |
| **v4** | **All 46 cases** | **46** | **0** | **0** |

These rows are not an improvement curve: the case sets differ, generation varies, and semantic grading involves judgment.

The [first design review](reviews/design-round-1.md) led to clearer distinctions between reading source and running code, a conditional beginner default, optional examples, and wording that covers reasoning as well as mechanisms. The [second design review](reviews/design-round-2.md) found no remaining design blocker.

Behavioral review still found weaknesses. A separate vocabulary checklist in v3 did not reliably prevent unexplained labels in secondary comparisons. Reviews also flagged an unexplained percentage-point distinction and an implicit causal connection in a boiling explanation. V4 gives ordinary meaning before technical labels, connects syntax names to visible code, and applies units and baselines to numerical explanations as well as formulas.

**One minor final concern remains in the record.** S32 scored 9/10 because the Chinese density explanation's last sentence could be read too categorically. Its intended condition for inferring density from mass alone is sound in context. The other 45 final responses scored 10/10. The coarse score does not imply perfect prose.

## Six-prompt blind comparison

These identical English prompts did not prescribe a word limit, table, or section template: dependency injection, entropy weights, OAuth versus JWT, a JavaScript `finally` return, opportunity cost, and a confusing confidence-interval explanation.

| Guidance | Mean words | Pass | Mean reviewer score |
| --- | ---: | ---: | ---: |
| **Clear Explanations v4** | **189.7** | **6/6** | **10.00/10** |
| No added skill | 235.3 | 6/6 | 9.83/10 |
| plain-language | 257.3 | 6/6 | 9.67/10 |
| explain | 276.3 | 5/6 | 8.83/10 |

V4 used about **19% fewer words** than the no-added-skill condition on these prompts. Answers were anonymized and reordered independently for each prompt before the final review. The partial comparison answer correctly distinguished JWT and OAuth but introduced unexplained terminology and unnecessary presentation overhead.

An earlier six-prompt comparison with explicit style constraints reached the scoring ceiling for every variant; it did not establish a quality ranking. [Earlier judgments](reviews/earlier-comparison-reviews.json) of the same natural comparison answers are preserved to show reviewer variation. The table above uses the final blind review.

Word counts use the harness's Unicode token convention, including numbers and code. This small, selected comparison is descriptive; it does not establish universal superiority.

## Method and limits

- Respondents received frozen instructions and exact prompts, without answer criteria or earlier review feedback. Fresh contexts were used per batch; **four to sixteen requests shared a batch**.
- Reviews used separate contexts but the same assistant model family. Observed model identifiers were unavailable and remain `null`.
- Code and arithmetic were checked where practical. The JavaScript scheduling checks used Node plus semantic review of browser behavior; they were not a browser execution benchmark.
- A pass required at least 9/10 across accuracy, clarity, coverage, structure, and fit, plus essential criteria and explicit constraints. Formatting checks alone could not establish quality.
- S25–S36 were withheld during v2 development, and H01–H04 were new after v3 was frozen. **Every final v4 case was a regression case after prior inspection.**
- No human comprehension study, cross-model study, automatic skill-selection benchmark, or reliable latency benchmark was performed.
- Direct Codex CLI execution failed during initialization in the original environment. The **194 live answers came from collaboration agents**; the included CLI adapter was checked with synthetic fixtures.

The harness separately passed **20 synthetic checks** of transport, validation, hashes, missing responses, stale reviews, and safe report rendering. They are not additional explanation-quality scenarios.

## Inspect or reproduce

- [Full recorded example: JavaScript finally](examples/N04.md)
- [All 194 exact responses and reviews](results.jsonl)
- [Summary, hashes, and revision history](evidence.json)
- [Frozen skill versions](versions)
- [Run instructions](README.md)
- [Sources and attribution](../docs/sources.md)

The public export removes environment-specific paths and private file-service identifiers while retaining exact response text, hashes, scores, and rationales. Run `python evals/tools/check_reference.py` from the repository root to verify the published record. Current formatting checks and stored semantic reviews do not re-run the original model experiment.
