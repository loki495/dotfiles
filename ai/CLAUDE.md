# Claude Code entrypoint

The rules shared by every agent (Claude Code, Codex, agy, opencode) live in `RULES.md`; this
file only adds what is specific to Claude Code. Read the shared rules first.

@RULES.md
@CLAUDE.private.md

## Context window management

Every call re-reads the whole context. Past **~250k tokens**, tell Andres and offer `/handoff`
then a fresh session with `/takeover claude [profile] <session_id>` before new work (finish the
current step first); `/clear` is another option after the handoff. The context-budget hook enforces
the warning. Avoid `/model` switches and plugin reloads in a big session (each forces a full cache rewrite).

## Hooks

The hooks (push guard, commit gate, claim overlap, read guard, dibs block, stop gate, context budget, rule inject, Laravel
tooling) are documented in `~/dotfiles/README.md`, section "Hooks". The rule-inject hook delivers
the Dibs rules relevant to an action; a `git commit`/`git push` gets its rules as context.

@RTK.md
