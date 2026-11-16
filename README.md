# Clear Explanations

An agent skill for explaining code, concepts, and ideas in plain language while preserving the details that matter. It guides an assistant to answer the question first, define unfamiliar terms where they appear, and use a concrete example when it makes the explanation easier to follow.

The skill's name is **`explain-clearly`**. Its complete, canonical instructions are in [`SKILL.md`](SKILL.md), with no runtime dependencies. You can read the whole skill before installing it.

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

This natural-language request is scenario N04 from the recorded evaluation:

> Why does this JavaScript print what it does?

```javascript
function choose() {
  try { return "first"; }
  finally { return "second"; }
}
console.log(choose());
```

**Excerpt from the recorded v4 answer:**

> It prints:
>
> ```text
> second
> ```
>
> The `return` inside `finally` **replaces the return that was about to leave `try`**.
>
> 1. `try` evaluates `return "first"`, preparing to return `"first"`.
> 2. Before the function exits, it must run the `finally` block.
> 3. `finally` executes `return "second"`, which replaces the pending return. The caller therefore receives `"second"`.
>
> `console.log` prints the value returned by `choose()`, so it prints `second`.
>
> If `finally` finished normally, without its own `return` or `throw`, the pending return of `"first"` would take effect. Merely entering `finally` does not erase that return; the new `return` does.

See the [complete recorded example](evals/examples/N04.md), including its review. This illustrates one response; outputs vary with the model, surrounding instructions, and available context.

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

## Evaluation

The [recorded evaluation](evals/REPORT.md) includes **194 actual responses across 46 distinct scenarios**, spanning code, mathematics, science, everyday decisions, and English, Chinese, and German requests. Final v4 responses passed the project's rubric on **46/46 scenarios**. The harness has **20 separate synthetic checks** for transport and integrity.

Reviews were performed by models. The final scenarios are regression cases after development; these results do not establish general superiority, performance on unseen tasks, or measured human comprehension gains. The [report](evals/REPORT.md) describes the method and limitations. The [evidence summary](evals/evidence.json) and [complete responses and reviews](evals/results.jsonl) make the results inspectable.

To run your own evaluation, follow the [evaluation guide](evals/README.md). The optional harness uses the Python standard library and requires Python 3.10 or newer.

## Contributing and support

Maintained by [jamestesting0](https://github.com/jamestesting0). Open an [issue](https://github.com/jamestesting0/clear-explanations/issues) with the prompt, answer, agent or model, and relevant setup when an explanation fails or installation is unclear.

New unseen scenarios, clearer documentation, and harness fixes are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for the contribution workflow and checks.

## Sources and license

Clear Explanations is an original synthesis informed by other explanation skills and documentation guidance. [Sources and attribution](docs/sources.md) records those influences and the ideas they contributed.

Released under the [MIT License](LICENSE).
