# Global developer context — Andres

This is the entrypoint for Codex, agy and any other agent that reads `AGENTS.md`. Claude Code
reads `ai/CLAUDE.md`, which imports the same rules.

Before substantive project work, read these completely, in order:

1. `~/dotfiles/ai/RULES.md`, the single rule set shared by every agent (principles, hard rules, pointers).
2. `~/dotfiles/ai/rules.md`, the detailed rules exported from the Dibs `rule` records (`[rule N]` in
   `RULES.md` is a record id), and `~/.dotfiles-private/ai/rules.private.md` when it exists. Claude
   Code gets the relevant ones injected by a hook; you have no such hook, so read both files and
   re-check the rules for a `git commit`, `git push`, test or doc edit before doing it.
3. `~/dotfiles/ai/CLAUDE.private.md` when it exists (home-network notes).

Do not copy rule text into other files; link to the record id. Translate product-specific
terminology as follows:

- `CLAUDE.md` or `.claude/project.md` means the corresponding project instructions or notes; prefer a local `AGENTS.md` when one exists.
- A named Claude skill, command, or agent maps to the matching skill in your tool (Codex: `~/.codex/skills/claude-import-*`).
- Claude hooks describe desired quality gates, but they do not authorize writes, pushes, production access, or other external actions.
- Claude-only UI, notification, context-window, and OpenCode restart instructions do not apply to other agents.
- Preserve project notes under `.claude/`; they remain durable project context even though the directory name originated with Claude.
