# Global developer context — Andres

This is the entrypoint for Codex, agy and any other agent that reads `AGENTS.md`. Claude Code
reads `ai/CLAUDE.md`, which imports the same rules.

Before substantive project work, read `~/dotfiles/ai/RULES.md` completely. It is the single
rule set shared by every agent. Also read `~/dotfiles/ai/CLAUDE.private.md` when it exists
(home-network notes). Translate product-specific terminology as follows:

- `CLAUDE.md` or `.claude/project.md` means the corresponding project instructions or notes; prefer a local `AGENTS.md` when one exists.
- A named Claude skill, command, or agent maps to the matching skill in your tool (Codex: `~/.codex/skills/claude-import-*`).
- Claude hooks describe desired quality gates, but they do not authorize writes, pushes, production access, or other external actions.
- Claude-only UI, notification, context-window, and OpenCode restart instructions do not apply to other agents.

The following rules are duplicated here because they are non-negotiable:

- Collaboration runs through Dibs and Sessioneer: claim every Dibs task before working
  (`agentName` = `<agent>:<session name>:<conversation id>`), keep plans current the moment a
  step finishes or blocks, save lessons to Dibs, use `sessioneer --send/--peers` for short-lived
  coordination, release claims before you stop, and check `sessioneer --usage` so a quota
  cutoff never leaves a stale plan.
- Docs, tests and the feature atlas go in the same commit as the code; stamp the atlas with
  the master/main SHA when work merges there, before any push.
- Delete temporary branches (local and remote) after a successful merge.
- Never push without first stating the exact remote and branch and receiving explicit confirmation.
- Never force-push or rewrite a commit already pushed to a shared remote without explicit confirmation.
- Never delete, weaken, skip, or bypass a test merely to force a passing result without explicit confirmation.
- Never perform a real-world-visible action such as sending email/SMS, charging a card, calling a third-party write endpoint, or triggering a user-visible notification without confirmation.
- Detect the project type and inspect its actual branch/worktree/container layout before applying project-family conventions.
- Preserve project notes under `.claude/`; they remain durable project context even though the directory name originated with Claude.
- When a discovered bug, improvement, or investigation would distract from the current task or take substantial time, search Dibs and create or update a follow-up task with evidence and a next step before continuing. Keep unconfirmed findings explicit; do not silently expand the current task.
