# Evaluation harness

The runtime bundle is [SKILL.md](../SKILL.md) and [references](../references). These optional tools are for testing and improving it; they do not run during ordinary explanations. The [expanded benchmark protocol](advanced/protocol.json) adds long source packets, a validation split, sealed holdouts, and a separate evidence-support score.

## Current expanded benchmark

The [advanced report](advanced/REPORT.md) records **225 actual responses** across four versions on **60 new long prompts** and **six known short prompts**. V6 stopped after 27 responses; v4, v5, and final v7 each completed all 66. The original development, validation, and holdout labels are retained, but **all final v7 results are retrospective**. The [machine-readable evidence](advanced/evidence.json) binds exact inputs, raw responses, independent reviews, ordered generation batches, and frozen runtime files.

```sh
python evals/advanced/check.py --require-current
python evals/advanced/check.py --json
```

The checker recomputes the declared archive bindings, reporting outcomes, split summaries, and paired comparisons. It does not generate answers or judge whether a review is correct. Omit `--require-current` when checking historical evidence after intentionally changing the runtime.

Historical entry files are named `INSTRUCTIONS.md` to avoid making old versions discoverable as extra skills. To restore an archived bundle for a new run:

```sh
python evals/advanced/materialize.py --variant v7 --out evals/runs/frozen-v7
python evals/tools/evaluate.py packets --cases evals/advanced/cases.json --out evals/runs/replay-v7 --bundle replay=evals/runs/frozen-v7
```

Both output directories must be new. Materialization verifies archived bytes; it does not reproduce a response. The advanced report documents the original generation and review procedure, including its limits.

## Historical 46-case evidence

| File | Contents |
| --- | --- |
| [REPORT.md](REPORT.md) | Results, revisions, comparison, and limitations |
| [cases.json](cases.json) | 46 prompts and explicit constraints; no expected answers |
| [rubric.json](rubric.json) | Separate semantic criteria for the reviewer |
| [protocol.json](protocol.json) | Registered scoring policy and development history |
| [results.jsonl](results.jsonl) | 194 exact responses, reviews, hashes, and public provenance |
| [evidence.json](evidence.json) | Summary, file hashes, and revision record |
| [versions](versions) | Frozen v1–v4 instructions |
| [reviews](reviews) | Design reviews and earlier comparison judgments |

The public export preserves response text and scores. It omits environment-specific paths, private file-service links, and timestamps that do not establish generation latency. Each line in `results.jsonl` is one JSON object, identified by `variant` and `case_id`; its prompt is in `cases.json`.

Use **Python 3.10+**, with no third-party packages. Run the commands below from the repository root.

## Check the reference record

```sh
python evals/tools/check_reference.py
```

This recomputes historical response hashes, case hashes, word counts, deterministic constraints, and aggregate counts. It checks the frozen v4 release against its recorded hash, independently of the current skill. Add `--require-current` only when you specifically want to require the current skill to equal historical v4. It does not generate new answers or certify human comprehension.

To create a local HTML view of the published responses:

```sh
python evals/tools/check_reference.py --report evals/report.html
```

## Run a new evaluation

Freeze the current skill and prompts in a new run directory:

```sh
python evals/tools/evaluate.py packets --cases evals/cases.json --out evals/runs/current --bundle current=.
```

With an installed and authenticated Codex CLI, generate one answer per packet:

```sh
python evals/tools/evaluate.py run --run evals/runs/current --variant current --command-json '["python", "evals/tools/codex_adapter.py"]'
```

The JSON quoting above is suitable for Bash or PowerShell 7.3+ using Standard/Windows native argument passing. For this optional command on Windows, use a current PowerShell or WSL Bash; older shells handle embedded quotes differently. See [Microsoft's native-argument parsing guidance](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_parsing#passing-arguments-to-native-commands).

The adapter uses an ephemeral conversation and a temporary working directory with read-only tool access. It retains the existing account configuration. An external adapter for another model can accept a prompt on standard input and write only its answer to standard output. Alternatively, import exact answer files with `collect`; every command provides `--help`.

Keep the answer rubric and previous feedback out of the answering agent's context. Use a new run directory for revisions. Record the actual model and isolation properties when known; leave unknown values unknown. Installed skills and global instructions can influence a baseline, so keep the environment consistent and prevent the candidate from loading into a no-skill condition.

### Bundles and comparison conditions

`--bundle NAME=DIR` freezes exactly `SKILL.md` and direct `references/*.md`, records each file's bytes and hash, and injects their contents into each replay packet. It rejects symlinks, nonportable paths, and filename collisions. It does not recursively load a repository. Keep rubrics, cases, and past responses outside runtime references; filename checks cannot detect an answer key disguised as a guide.

This mode evaluates the guidance content with all references supplied. It does **not** establish that an agent selectively opens the right reference during native use. `--skill NAME=FILE` retains the original single-file behavior; `--skill NAME=none` creates a no-skill condition. You can combine several conditions in one packet command, for example `--bundle current=. --skill previous=evals/versions/v4.md`.

## Review separately

```sh
python evals/tools/evaluate.py check --run evals/runs/current
python evals/tools/evaluate.py review-template --run evals/runs/current --out evals/local-reviews/current.json
```

Give the prompt, answer, and corresponding criteria from `rubric.json` to a separate reviewer. Replace each `UNREVIEWED` entry with a reasoned judgment bound to that answer's exact hash. Core and fresh-case criteria use an `expected` wrapper; the six natural-prompt criteria are stored directly under their case IDs.

For the historical 46-case suite, score **accuracy, clarity, coverage, structure, and fit** from 0–2 each. A pass requires at least 9/10, essential coverage, and explicit constraint compliance. The expanded suite adds **evidence** as a sixth dimension and requires at least 11/12 under its [registered policy](advanced/protocol.json). A wrong central claim or invented evidence fails regardless of total. Semantically equivalent plain language satisfies a criterion without repeating its technical vocabulary.

```sh
python evals/tools/evaluate.py report --run evals/runs/current --reviews evals/local-reviews/current.json --out evals/report.html
```

`check` verifies record integrity and mechanical constraints; a zero exit code is not a semantic-quality verdict. Sentence counting is heuristic. Language, factual correctness, usefulness, section requirements, and code-only behavior require review. Reports preserve raw responses as escaped text.

### Blind review packets

```sh
python evals/tools/evaluate.py review-packets --run evals/runs/current --out evals/local-reviews/blind --key evals/local-reviews/private-map.json --rubric evals/rubric.json
```

Give only the `blind` directory to an independent reviewer. The command shuffles records, removes variant labels, and writes a review template; the separate private map binds identities and exact response hashes. It does not perform the review. Output style may still reveal a condition.

After the reviewer fills the template, import it with:

```sh
python evals/tools/evaluate.py review-import --run evals/runs/current --packets evals/local-reviews/blind --key evals/local-reviews/private-map.json --reviews evals/local-reviews/blind/completed.json --out evals/local-reviews/current.json
```

Both commands accept repeated `--run` arguments. Import rejects missing or changed source packets and duplicate or mismatched reviews. Partial review coverage is allowed and remains visibly unreviewed. Review scores are judgments, not generated mechanical-quality claims.

## Harness checks

```sh
python evals/tools/test_harness.py
python evals/tools/test_codex_adapter.py
python evals/advanced/test_check.py
python evals/advanced/test_materialize.py
```

These are synthetic transport and integrity checks, separate from explanation scenarios. The recorded live responses used collaboration agents because direct Codex initialization failed in the original environment; the adapter's reference checks are synthetic.

S25–S36 were held out during v2 development. H01–H04 were added after v3 was frozen. All 46 were known regression cases by final v4. Add new unseen scenarios when assessing whether a future change generalizes.
