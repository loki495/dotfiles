---
name: ai-config
description: How Andres's shared AI-agent config in ~/dotfiles/ai is wired for Claude Code, opencode, Codex and agy — portability rules for skills/commands/agents, the Codex wrapper and opencode agent copies to add alongside, and when opencode must be restarted. Use before adding or changing anything under ~/dotfiles/ai or opencode/Codex/agy config.
---

# Shared config across agents

Everything under `~/dotfiles/ai/` is shared, not Claude-only. opencode links `commands/` and
`skills/` directly and has its own agent copies in `agents-opencode/`. Codex reads
`AGENTS.md` (which points back to `CLAUDE.md`) plus one wrapper skill per item in
`codex-skills/claude-import-<name>/`. Antigravity's `agy` discovers `skills/` through
`gemini-config-skills.json`. When adding or changing a skill, command, or agent:

- Keep it portable: plain Markdown, `SKILL.md` frontmatter limited to `name` and
  `description`, and `$ARGUMENTS` for command input. Describe actions in tool-neutral
  terms (e.g. "ask the user"), or name a fallback when a step depends on a Claude Code-only
  tool, hook, or slash command.
- Add or update the matching `codex-skills/claude-import-<name>/SKILL.md` wrapper (it points
  at the shared file and repeats any safety rule, like push confirmation). The install
  script's Codex section links every wrapper in that directory.
- For a new agent, add the opencode copy in `agents-opencode/` too.
- Claude-only pieces (hooks, `settings.json`, plugins) don't exist for the other agents.
  When a rule is enforced by a hook, keep the rule written in `CLAUDE.md` as well, so agents without
  the hook still follow it.

## opencode restart requirement

opencode loads its config, agents, commands, skills, and plugins **once when it starts** — it is
not hot-reloaded. After any of these change, the **opencode serve process must be restarted**
(quit and relaunch opencode entirely; closing/reopening an individual session is NOT enough, the
running server keeps the already-loaded config):

- `opencode.json` / `opencode.jsonc` (any field)
- `~/.config/opencode/agent(s)/` — agent files
- `~/.config/opencode/command(s)/` — command files
- `~/.config/opencode/skill(s)/<name>/SKILL.md` — skill definitions
- `~/.config/opencode/plugin(s)/` or any `plugin:` listed JS/TS plugin
- any file referenced by `instructions` (e.g. `~/.claude/CLAUDE.md`) that changes system context
