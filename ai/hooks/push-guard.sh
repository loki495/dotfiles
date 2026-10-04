#!/usr/bin/env bash
# PreToolUse(Bash): any git push must go through an explicit permission prompt,
# even when allow rules or the permission mode would otherwise let it run silently.
cmd=$(jq -r '.tool_input.command // ""')
if grep -Eq '(^|[^[:alnum:]_-])git([[:space:]]+-[^[:space:]]+([[:space:]]+[^-[:space:]][^[:space:]]*)?)*[[:space:]]+push([[:space:]]|$)' <<<"$cmd"; then
  jq -n --arg c "$cmd" '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "ask",
    permissionDecisionReason: ("git push needs explicit confirmation (branch + remote): " + $c)}}'
fi
exit 0
