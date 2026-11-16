# Evaluation harness

The skill itself is [SKILL.md](../SKILL.md). These optional tools are for testing and improving it; they do not run during ordinary explanations.

## Recorded evidence

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

This recomputes response hashes, case hashes, word counts, deterministic constraints, and aggregate counts. It also checks that the current skill matches the frozen release. It does not generate new answers or certify human comprehension.

To create a local HTML view of the published responses:

```sh
python evals/tools/check_reference.py --report evals/report.html
```

## Run a new evaluation

Freeze the current skill and prompts in a new run directory:

```sh
python evals/tools/evaluate.py packets --cases evals/cases.json --out evals/runs/current --skill current=SKILL.md
```

With an installed and authenticated Codex CLI, generate one answer per packet:

```sh
python evals/tools/evaluate.py run --run evals/runs/current --variant current --command-json '["python", "evals/tools/codex_adapter.py"]'
```

The JSON quoting above is suitable for Bash or PowerShell 7.3+ using Standard/Windows native argument passing. For this optional command on Windows, use a current PowerShell or WSL Bash; older shells handle embedded quotes differently. See [Microsoft's native-argument parsing guidance](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_parsing#passing-arguments-to-native-commands).

The adapter uses an ephemeral conversation and a temporary working directory with read-only tool access. It retains the existing account configuration. An external adapter for another model can accept a prompt on standard input and write only its answer to standard output. Alternatively, import exact answer files with `collect`; every command provides `--help`.

Keep the answer rubric and previous feedback out of the answering agent's context. Use a new run directory for revisions. Record the actual model and isolation properties when known; leave unknown values unknown. Installed skills and global instructions can influence a baseline, so keep the environment consistent and prevent the candidate from loading into a no-skill condition.

## Review separately

```sh
python evals/tools/evaluate.py check --run evals/runs/current
python evals/tools/evaluate.py review-template --run evals/runs/current --out evals/local-reviews/current.json
```

Give the prompt, answer, and corresponding criteria from `rubric.json` to a separate reviewer. Replace each `UNREVIEWED` entry with a reasoned judgment bound to that answer's exact hash. Core and fresh-case criteria use an `expected` wrapper; the six natural-prompt criteria are stored directly under their case IDs.

Score **accuracy, clarity, coverage, structure, and fit** from 0–2 each. A pass requires at least 9/10, essential coverage, and explicit constraint compliance. A wrong central claim or invented evidence fails regardless of total. Semantically equivalent plain language satisfies a criterion without repeating its technical vocabulary.

```sh
python evals/tools/evaluate.py report --run evals/runs/current --reviews evals/local-reviews/current.json --out evals/report.html
```

`check` verifies record integrity and mechanical constraints; a zero exit code is not a semantic-quality verdict. Sentence counting is heuristic. Language, factual correctness, usefulness, section requirements, and code-only behavior require review. Reports preserve raw responses as escaped text.

## Harness checks

```sh
python evals/tools/test_harness.py
python evals/tools/test_codex_adapter.py
```

These are **20 synthetic transport and integrity checks**, separate from the 46 explanation scenarios. The recorded live responses used collaboration agents because direct Codex initialization failed in the original environment; the adapter's reference checks are synthetic.

S25–S36 were held out during v2 development. H01–H04 were added after v3 was frozen. All 46 were known regression cases by final v4. Add new unseen scenarios when assessing whether a future change generalizes.
