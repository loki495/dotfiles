# Claude Code entrypoint

The rules shared by every agent (Claude Code, Codex, agy, opencode) live in `RULES.md`; this
file only adds what is specific to Claude Code. Read the shared rules first.

@RULES.md
@CLAUDE.private.md

## Context window management

Every call re-reads the whole context. Past **~250k tokens**, tell Andres and offer `/handoff`
then `/clear` before new work (finish the current step first); the context-budget hook enforces
it. Avoid `/model` switches and plugin reloads in a big session (each forces a full cache rewrite).

## Hooks

The hooks (push guard, commit gate, claim overlap, stop gate, context budget, rule inject, Laravel
tooling) are documented in `~/dotfiles/README.md`, section "Hooks". The rule-inject hook delivers
the Dibs rules relevant to an action; a denied `git commit`/`git push` carries them, re-run to proceed.

@RTK.md
