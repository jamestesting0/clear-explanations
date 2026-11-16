# Sources and attribution

Clear Explanations uses original wording and a synthesis of ideas from the sources below. The development provenance records these influences; no source skill was concatenated or copied verbatim into the canonical [`SKILL.md`](../SKILL.md).

The links identify the upstream projects and documents. Links to moving branches may change after the v4 evaluation recorded on November 16, 2026. Attribution describes an influence on this project, not an endorsement by an upstream author.

## Skill design

| Source | Ideas used in Clear Explanations |
| --- | --- |
| [Extended Karpathy Guidelines](https://github.com/jamestesting0/extended-karpathy-guidelines/blob/main/SKILL.md) | Compact conventions and a clear scope. The explanation skill keeps its purpose separate from a coding workflow. |
| [plain-language — arjunprabhulal/agent-skills](https://github.com/arjunprabhulal/agent-skills/blob/main/skills/docs/plain-language/SKILL.md) | Teach necessary terms, preserve precision, and keep the central idea in focus. |
| [explain — FlorianBruniaux/claude-code-ultimate-guide](https://github.com/FlorianBruniaux/claude-code-ultimate-guide/blob/main/examples/skills/explain/SKILL.md) | Adjust depth to the reader and choose useful structures and comparison criteria. |
| [code-explainer — Microsoft Waza](https://github.com/microsoft/waza/blob/main/examples/code-explainer/SKILL.md) | Lead with the result, ground code explanations in the source, and connect inputs to outputs. |
| [wait-what — Matt Pocock](https://github.com/mattpocock/skills/blob/main/skills/productivity/wait-what/SKILL.md) | Change the approach when an explanation does not land. |
| [eli5 — Cloudflare Docs](https://github.com/cloudflare/cloudflare-docs/blob/production/.agents/skills/eli5/SKILL.md) | Preserve technical accuracy and identify the limits of an analogy. The broader document workflow was outside this skill's scope. |

The comparison runs used the following source snapshots. A hash identifies the bytes evaluated; it is not a claim about the current upstream version.

| Compared skill | Snapshot date | SHA-256 |
| --- | --- | --- |
| `plain-language` | 2026-11-16 | `5e146a79331ef0bab7a5d41e3735327d77e41fad51ba1cd2cb9eb0db578ee9e8` |
| `explain` | 2026-11-16 | `05c2565bcbbed3890dc9af6cab4039cda49d97c0906d4bb85a5ddb13126de324` |

The [evaluation report](../evals/REPORT.md) explains the comparison method and its limits. The [response archive](../evals/results.jsonl) preserves the recorded outputs and reviews. These small comparisons do not establish general superiority over another skill.

## README and documentation

The README's structure follows these primary guides, consulted on November 16, 2026:

| Source | Application to this repository |
| --- | --- |
| [GitHub Docs: About the repository README file](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes) | Explain the project's purpose, usefulness, first steps, support, and maintainers. Use relative links to repository material and keep the entry point concise. |
| [Write the Docs: How to write software documentation](https://www.writethedocs.org/guide/writing/beginners-guide-to-docs/) | Include a small common-use example, short basic installation instructions, contribution and support paths, and the license. |
| [Open Source Guides: Starting an Open Source Project](https://opensource.guide/starting-a-project/) | State what users can do and set clear expectations for participating in the project. |
| [Diátaxis: Diátaxis as a guide to work](https://diataxis.fr/how-to-use-diataxis/) | Add documentation that serves a concrete need, without imposing empty categories or a large documentation structure. |

## Installation references

Installation and discovery behavior depend on the agent, its version, and its selected harness. The [installation guide's official sources](installation.md#official-sources) links the Skills installer and host documentation used for this release, alongside the relevant compatibility details.

## License

This repository's original material is available under the [MIT License](../LICENSE). The linked upstream projects retain their own licenses and attribution requirements.
