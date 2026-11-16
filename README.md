# Clear Explanations

An agent skill for explaining code, concepts, and ideas in plain language while preserving the details that matter. It guides an assistant to answer the question first, define unfamiliar terms where they appear, and use a concrete example when it makes the explanation easier to follow.

The skill's name is **`explain-clearly`**. [`SKILL.md`](SKILL.md) is the entry point, with three optional Markdown guides for difficult questions. The runtime bundle has no code dependencies and can be inspected before installation.

## Install

From the project where you want the skill available, run:

```sh
npx skills add jamestesting0/clear-explanations --skill explain-clearly
```

Choose your agents when prompted and keep the default **symlink** installation. For a project install, the installer keeps the shared skill in `.agents/skills/explain-clearly` and creates the appropriate agent paths, such as `.claude/skills/explain-clearly` for Claude Code.

To install for your user account across projects, add `--global`:

```sh
npx skills add jamestesting0/clear-explanations --skill explain-clearly --global
```

The current installer requires **Node.js 22.20 or newer**. The skill itself is Markdown; Node.js is an installer requirement. Agent discovery depends on the host and its configuration. See the [installation guide](docs/installation.md) for supported paths, manual installation, activation, and troubleshooting.

## Example

This natural-language request is N04 from the recorded evaluation:

Why does this JavaScript print what it does?
```javascript
function choose() {
  try { return "first"; }
  finally { return "second"; }
}
console.log(choose());
```

**Recorded v7 answer:**

> It prints:
>
> ```text
> second
> ```
>
> The `finally` block runs **before the function finishes returning**, even when the `try` block has reached a `return`.
>
> 1. `return "first"` prepares to return `"first"`.
> 2. Before that return completes, JavaScript runs `finally`.
> 3. `return "second"` replaces the pending return, so `choose()` returns `"second"`.
>
> Then `console.log` prints that single returned value. `"first"` never reaches it.
>
> If `finally` finished normally—without its own `return` or a thrown error—the original `"first"` return would continue.

See the [complete recorded example](evals/advanced/examples/N04.md), including its review. Outputs vary with the model, instructions, and available context.

## When to use it

Use it for explanations, code walkthroughs, comparisons, or a second attempt at something that did not make sense. Once your agent has loaded the skill, try:

- “I know basic Java but not Spring. What does dependency injection actually mean?”
- “Why does changing one row change all three rows in this Python list?”
- “I am lost. Explain that again with a smaller example.”

The skill is scoped to explanation requests. Implementation-only tasks and ordinary copyediting are outside its intended scope.

## How it guides the answer

- **Start with the answer.** Establish the central idea before adding background.
- **Ground the explanation.** Inspect supplied material and separate supported behavior from inference or execution evidence.
- **Connect the steps.** Explain what changes and why the next step follows.
- **Define terms in context.** Preserve useful technical vocabulary and explain unfamiliar terms when they first appear.
- **Adapt to the reader.** Choose the detail, example, and structure that the question needs.

Explicit requests for length, language, format, and depth take precedence over the skill's defaults. Its final check asks the agent to verify examples and remove repetition while preserving conditions and uncertainty.

### Optional reference guides

| Guide | What it adds |
| --- | --- |
| [Evidence and sources](references/evidence-and-sources.md) | Match claims to applicable evidence, resolve version or scope conflicts, distinguish inference from observation, and cite the support actually available. |
| [Explanation patterns](references/explanation-patterns.md) | Handle long requests, code state changes, quantitative reasoning, mechanisms, interpretations, and decisions without losing essential connections. |
| [Worked examples](references/worked-examples.md) | Six original examples showing useful code traces, numerical comparisons, source reconciliation, uncertainty, interpretation, and a one-sentence answer. |

The core tells the agent when each guide is useful. Simple questions can use the core alone. Writing references support the skill's design; facts in an explanation still need evidence appropriate to the user's question.

## Evaluation

The [expanded benchmark](evals/advanced/REPORT.md) adds **60 long, tricky prompts** averaging **545 whitespace tokens**—about **11.3 times** the previous suite's mean length—and **six known short-question checks**. Four recorded versions produced **225 actual responses**, each independently reviewed.

| Version | Long prompts passed | Short prompts passed | Outcome |
| --- | ---: | ---: | --- |
| Previous v4 | 60/60 | 6/6 | Strong baseline |
| Expanded v5 | 59/60 | 6/6 | One partial: unsupported negative claim |
| Revised v6 | 26/27 generated | Not generated | Stopped after one arithmetic failure |
| Final v7 | 60/60 | 6/6 | Complete retrospective retest |

Two design-review rounds, additional revision reviews, and independent answer audits informed the changes. Failed answers and conflicting reviews remain public. **All final v7 cases are retrospective**, and v6 has incomplete coverage. The baseline already passed the long suite; model review does not establish universal superiority or measured human comprehension.

The harness has **81 separate synthetic software tests**. Browse the [case catalogue](evals/advanced/CASES.md), [exact evidence](evals/advanced/evidence.json), and [evaluation guide](evals/README.md). The earlier [194-response study across 46 scenarios](evals/REPORT.md) remains intact. Optional tools use the Python standard library and require Python 3.10+.

## Contributing and support

Maintained by [jamestesting0](https://github.com/jamestesting0). Open an [issue](https://github.com/jamestesting0/clear-explanations/issues) with the prompt, answer, agent or model, and relevant setup when an explanation fails or installation is unclear.

New unseen scenarios, clearer documentation, and harness fixes are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for the contribution workflow and checks.

## Sources and license

Clear Explanations is an original synthesis informed by other explanation skills and documentation guidance. [Sources and attribution](docs/sources.md) records those influences and the ideas they contributed.

Released under the [MIT License](LICENSE).
