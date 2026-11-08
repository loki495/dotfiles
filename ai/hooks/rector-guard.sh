#!/usr/bin/env bash
# PreToolUse(Bash): deny `rector process` (or `composer rector:apply`) without --dry-run.
# Rector output is never auto-applied; Andres reviews the dry-run diff and applies it himself.
cmd=$(jq -r '.tool_input.command // ""' <<<"$(cat)")
if grep -Eq '(^|[^[:alnum:]_-])(rector[[:space:]]+process|composer[[:space:]]+(run[[:space:]]+)?rector:apply)([[:space:]]|$|[;&|"'"'"')])' <<<"$cmd" \
   && ! grep -q -- '--dry-run' <<<"$cmd"; then
  jq -n '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny",
    permissionDecisionReason: "Rector runs with --dry-run only; show Andres the diff and let him apply it (skill laravel-conventions, Rector)."}}'
fi
exit 0
