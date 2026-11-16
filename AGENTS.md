# Working on Clear Explanations

For explanation requests in this repository, read `SKILL.md` and apply its guidance. The skill is named `explain-clearly`; the repository is named `clear-explanations`.

## Scope

- Keep `SKILL.md` as the sole canonical skill. Its runtime instructions must remain self-contained and agent-neutral.
- Keep installation details in `docs/installation.md` and evaluation procedures in `evals/README.md`.
- Use the standard skills installer and documented native locations. Do not add duplicate instruction copies for each agent.
- Put the useful setup and example first in the README. Keep detailed evidence and qualifications in the linked evaluation guide.

## Verification

Use the checks appropriate to the change, as described in `CONTRIBUTING.md`. Documentation edits do not require regenerating the explanation suite. Changes to the skill's behavior require new response evidence and a separate review.

The recorded v4 instructions and responses are historical evidence. Do not silently edit them, relabel regression cases as unseen, or treat synthetic harness checks as model-quality tests. Preserve exact response hashes and label the scope of every result.
