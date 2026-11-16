# Installation

[README](../README.md) · [Skill instructions](../SKILL.md) · [License](../LICENSE)

The repository's root `SKILL.md` is the canonical entry point, with optional supporting guides in `references/`. Install the complete runtime bundle into the project where you want to use it, or into your user account for use across projects. You do not need a custom installer or separate editions of the skill for each agent.

## Requirements

- **The skill:** plain Markdown, with no runtime dependencies.
- **The standard installer:** Node.js **22.20 or later**, as specified by the current [Vercel skills CLI documentation](https://github.com/vercel-labs/skills).
- **Optional evaluation tools:** Python **3.10 or later**. Running evaluations is separate from installing or using the skill.

## Standard installation

From your target project's directory, run:

```sh
npx skills add jamestesting0/clear-explanations --skill explain-clearly
```

Select the agents you use. Choose the recommended **Symlink** method when prompted. The installer discovers the repository's root `SKILL.md` and installs it under the skill name `explain-clearly`.

For all projects on the current machine, use:

```sh
npx skills add jamestesting0/clear-explanations --skill explain-clearly --global
```

To select Codex, Claude Code, Cursor, Gemini CLI, GitHub Copilot, and OpenCode explicitly:

```sh
npx skills add jamestesting0/clear-explanations --skill explain-clearly -a codex -a claude-code -a cursor -a gemini-cli -a github-copilot -a opencode
```

Add `--global` to that command if you want user scope. These single-line commands also work in Windows terminals with Node.js installed.

### Where it goes

In the installer's default symlink mode, the shared copy is:

| Scope | Canonical installed file |
| --- | --- |
| Current project | `.agents/skills/explain-clearly/SKILL.md` |
| Current user | `~/.agents/skills/explain-clearly/SKILL.md` |

Codex, Cursor, Gemini CLI, GitHub Copilot, and OpenCode support the shared `.agents/skills` location. Claude Code uses `.claude/skills`, so the installer adds a link from `.claude/skills/explain-clearly` to the shared folder, or the corresponding user-level locations for a global install.

The Agent Skills format makes the content portable; discovery locations and optional features still depend on the agent. Installing a skill makes it available for relevant tasks, but does not guarantee that the agent invokes it for every explanation. You can explicitly ask it to use `explain-clearly`.

### Windows

Run the same commands in PowerShell or Command Prompt. The current installer implementation uses directory junctions on Windows and falls back to a copy if it cannot create a link. If an agent does not expose the linked skill, rerun the install with `--copy`:

```sh
npx skills add jamestesting0/clear-explanations --skill explain-clearly --copy
```

Keep `--global` if that was your original scope. Copy mode creates independent agent-specific copies, which need to be kept updated. Install in the environment where your agent runs; Windows, WSL, and remote machines can have different home directories.

### VS Code

Select the agent running inside VS Code: Copilot, Claude, or Codex. There is no separate `vscode` target in the installer. The selected harness determines supported locations and controls.

If Copilot does not expose the shared `.agents/skills` installation, its documented native project location is `.github/skills/explain-clearly/SKILL.md`. Copy the complete installed skill folder to `.github/skills/explain-clearly/` as an explicit fallback and keep that copy in sync when updating. Use **Chat: Open Customizations → Skills** to inspect the selected harness's skills. Claude and Codex should use their own documented locations.

## Verify and troubleshoot

1. **Check source discovery.** This lists the repository's available skills without installing them:

   ```sh
   npx skills add jamestesting0/clear-explanations --list
   ```

   Look for `explain-clearly`. This checks the package's discoverability, not an IDE's activation behavior.

2. **Check the installed scope.** Run `npx skills list` from the target project, or `npx skills list --global` for user installations. Confirm the expected `SKILL.md` exists in a supported location.

3. **Refresh the agent.** Refresh its skill list or open a new agent session if the skill does not appear. Gemini CLI provides `/skills reload` and `/skills list`. In VS Code, inspect Skills for the selected harness.

4. **Check the path and link.** The containing folder should be named `explain-clearly`, matching the frontmatter `name`. For Claude, confirm its `.claude/skills/explain-clearly` entry resolves to the skill. Use the Windows copy fallback or the explicit Copilot location above when needed.

5. **Try explicit invocation.** Ask, “Use explain-clearly to explain how this function works.” If it still does not load, check the client's skill settings, permissions, version, and any competing installation with the same name. User-level skills on your local machine are not automatically available in every cloud or remote session.

## Manual installation

For a dependency-free install, download the repository and create this directory inside your target project:

```text
.agents/skills/explain-clearly/
```

Copy the repository's [SKILL.md](../SKILL.md) into it as `SKILL.md`, copy the complete [references](../references) directory beside it, and include [LICENSE](../LICENSE) when redistributing it. Preserve the relative paths: `SKILL.md` links to the three reference files. Evaluation files and documentation are not needed at runtime.

For user scope, use `.agents/skills/explain-clearly/` inside your home directory. For a Claude-only manual installation, use `.claude/skills/explain-clearly/` instead. The standard installer is the convenient option when you want shared storage plus the Claude alias.

### AGENTS.md fallback

For an agent that reads project instructions but does not discover skills, first put the skill at the project path above. Then **append** this section to your existing `AGENTS.md`:

```markdown
## Clear explanations

When the user asks for an explanation, walkthrough, comparison, or simpler
wording, read `.agents/skills/explain-clearly/SKILL.md` before answering and
apply its guidance. Use it only for explanation tasks.
```

This is an instruction to read a file; it does not register a native skill or create a slash command. If your agent uses another project-instructions file, add the same instruction there. You can also ask the agent directly to read the file by path. Preserve the project's existing instructions.

## Installation check

The v7 runtime was installed from the local release checkout into an isolated Linux project with **skills 1.9.0**, selecting Codex, Claude Code, Cursor, Gemini CLI, GitHub Copilot, and OpenCode. Source discovery found one skill. The core and all three references matched the frozen v7 files byte for byte, and the Claude alias resolved to the shared directory.

The standard installer also copies repository documentation and optional evaluation material; only the core and references provide runtime guidance. These checks establish installer discovery, file layout, and exact runtime bytes. Native agent invocation and Windows were not exercised.

The [v7 local check](installation-check-v7-local.json) records the selected targets, runtime hashes, and observed scope. Earlier [v5](installation-check-v5-local.json) and [v4](installation-check.json) records remain as historical evidence.

## Official sources

Discovery and installation details checked **2026-11-16**. These notes are based on official documentation and installer source; they do not claim that every IDE or Windows environment has been exercised.

| Topic | Primary sources |
| --- | --- |
| Portable format and discovery conventions | [Agent Skills specification](https://agentskills.io/specification), [client implementation guide](https://agentskills.io/client-implementation/adding-skills-support) |
| Standard installer, commands, and root `SKILL.md` discovery | [Vercel skills README](https://github.com/vercel-labs/skills), [CLI reference](https://github.com/vercel-labs/skills/blob/main/docs/commands.md), [creating skills](https://github.com/vercel-labs/skills/blob/main/docs/creating-skills.md) |
| Canonical storage, agent mappings, and Windows link behavior | [Installer implementation](https://github.com/vercel-labs/skills/blob/main/src/installer.ts), [agent mappings](https://github.com/vercel-labs/skills/blob/main/src/agents.ts) |
| Codex | [Build skills](https://learn.chatgpt.com/docs/build-skills) |
| Claude Code | [Skills](https://code.claude.com/docs/en/skills), [project instructions and AGENTS.md](https://code.claude.com/docs/en/memory) |
| GitHub Copilot and VS Code | [Copilot skills](https://docs.github.com/en/copilot/concepts/customizations/agent-skills), [Copilot CLI reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference), [VS Code skills guide](https://code.visualstudio.com/docs/agent-customization/agent-skills) |
| Cursor, Gemini CLI, and OpenCode | [Cursor skills](https://cursor.com/docs/skills), [Gemini CLI skills](https://geminicli.com/docs/cli/skills/), [OpenCode skills](https://opencode.ai/docs/skills/) |
| Instruction-file fallback | [AGENTS.md](https://agents.md/) |
