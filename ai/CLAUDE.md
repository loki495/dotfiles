# Claude Code entrypoint

The rules shared by every agent (Claude Code, Codex, agy, opencode) live in `RULES.md`; this
file only adds what is specific to Claude Code. Read the shared rules first.

@RULES.md
@CLAUDE.private.md

## Context window management

Every call re-reads the whole context. Decide continue, park or rotate by skill `session-flow`
(state table; numbers in its `thresholds.conf`), and ask any offer with AskUserQuestion. `/rotate`
runs that decision and the launch; `/takeover claude [profile] <session_id>` is only for a session
that ended or died without a handoff. The context-budget hook reads the same thresholds file. Avoid
`/model` switches and plugin reloads in a big session (each forces a full cache rewrite).

## Hooks

The hooks (push guard, commit gate, claim overlap, read guard, dibs block, stop gate, context budget, rule inject, Laravel
tooling) are documented in `~/dotfiles/README.md`, section "Hooks". The rule-inject hook delivers
the Dibs rules relevant to an action; a `git commit`/`git push` gets its rules as context.

@RTK.md
