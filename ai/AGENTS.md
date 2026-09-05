# Global developer context — Andres

This is the Codex entrypoint for Andres's maintained cross-agent setup.

Before substantive project work, read `~/dotfiles/ai/CLAUDE.md` completely. Treat it as global developer context and translate product-specific terminology as follows:

- `CLAUDE.md` or `.claude/project.md` means the corresponding project instructions or notes; prefer a local `AGENTS.md` when one exists.
- A named Claude skill, command, or agent maps to the matching Codex skill under `~/.codex/skills/claude-import-*`.
- Claude hooks describe desired quality gates, but they do not authorize writes, pushes, production access, or other external actions.
- Claude-only UI, notification, context-window, and OpenCode restart instructions do not apply to Codex.

The following safety rules are duplicated here because they are non-negotiable:

- Never push without first stating the exact remote and branch and receiving explicit confirmation.
- Never force-push or rewrite a commit already pushed to a shared remote without explicit confirmation.
- Never delete, weaken, skip, or bypass a test merely to force a passing result without explicit confirmation.
- Never perform a real-world-visible action such as sending email/SMS, charging a card, calling a third-party write endpoint, or triggering a user-visible notification without confirmation.
- Detect the project type and inspect its actual branch/worktree/container layout before applying project-family conventions.
- Preserve project notes under `.claude/`; they remain durable project context even though the directory name originated with Claude.

