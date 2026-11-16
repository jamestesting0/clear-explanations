# Contributing

Clear Explanations has one canonical instruction file: [SKILL.md](SKILL.md). Keep it portable, compact, and focused on helping a reader understand the question they asked.

## Useful contributions

- Report a confusing explanation with the original prompt, actual response, agent or model, and relevant settings. Remove secrets and private project details.
- Add realistic scenarios that expose a missing prerequisite, inaccurate simplification, unnecessary verbosity, or poor structure. Include the expected behavior separately from the prompt.
- Fix a reproducible installation or evaluation-harness problem.

Open an [issue](https://github.com/jamestesting0/clear-explanations/issues) or a focused pull request. Explain the problem, the change, and the checks that support it.

## Verification

Run these commands from the repository root with Python 3.10 or later:

```sh
python evals/tools/check_reference.py
python evals/tools/test_harness.py
python evals/tools/test_codex_adapter.py
```

The first command checks the published reference evidence. The other two check the harness with synthetic fixtures; they do not measure explanation quality.

For documentation-only changes, check the changed instructions and links. For harness changes, run the relevant harness checks. For changes to explanation behavior, generate new answers for affected scenarios and a suitable set of unseen prompts, then obtain a separate semantic review. See [the evaluation guide](evals/README.md).

Preserve historical responses and reviews. Record a new version instead of editing an old answer to make it pass. Keep expected answers away from the answering agent, record failed runs, and distinguish documented compatibility from an installation you actually exercised.

Contributions are provided under the repository's [MIT license](LICENSE).
