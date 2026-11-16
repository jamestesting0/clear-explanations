# Contributing

Clear Explanations has one canonical entry point: [SKILL.md](SKILL.md), with optional runtime guides in [references](references). Keep the core portable, compact, and sufficient for simple questions. Supporting files should help with a specific explanation difficulty without duplicating the core or loading evaluation answers.

## Useful contributions

- Report a confusing explanation with the original prompt, actual response, agent or model, and relevant settings. Remove secrets and private project details.
- Add realistic scenarios that expose a missing prerequisite, inaccurate simplification, unnecessary verbosity, or poor structure. Include the expected behavior separately from the prompt.
- Fix a reproducible installation or evaluation-harness problem.

Open an [issue](https://github.com/jamestesting0/clear-explanations/issues) or a focused pull request. Explain the problem, the change, and the checks that support it.

## Verification

Run these commands from the repository root with Python 3.10 or later:

```sh
python evals/tools/check_reference.py
python evals/advanced/check.py --require-current
python evals/tools/test_harness.py
python evals/tools/test_codex_adapter.py
python evals/advanced/test_check.py
python evals/advanced/test_materialize.py
```

The first two commands verify the historical and expanded evidence archives. The remaining commands check the harness with synthetic fixtures; they do not measure explanation quality. After an intentional runtime change, use the advanced checker without `--require-current` to verify the historical archive, and generate new responses before claiming results for the changed bundle.

For documentation-only changes, check the changed instructions and links. For harness changes, run the relevant harness checks. For changes to explanation behavior, generate new answers for affected scenarios and a suitable set of unseen prompts, then obtain a separate semantic review. See [the evaluation guide](evals/README.md).

Preserve historical responses and reviews. Record a new version instead of editing an old answer to make it pass. Keep expected answers away from the answering agent, record failed runs, and distinguish documented compatibility from an installation you actually exercised.

Contributions are provided under the repository's [MIT license](LICENSE).
