#!/usr/bin/env bash
# PreToolUse(Bash): any git push must go through an explicit permission prompt,
# even when allow rules or the permission mode would otherwise let it run silently.
# It is denied outright when the repo's feature atlas is stale for the branch being pushed
# (a subsystem's owned files changed since its Verified at); Dibs trouble skips only that check.
# HELPER overrides the atlas helper (tests).
input=$(cat)
cmd=$(jq -r '.tool_input.command // ""' <<<"$input")
if grep -Eq '(^|[^[:alnum:]_-])git([[:space:]]+-[^[:space:]]+([[:space:]]+[^-[:space:]][^[:space:]]*)?)*[[:space:]]+push([[:space:]]|$)' <<<"$cmd"; then
  cwd=$(jq -r '.cwd // empty' <<<"$input")
  helper=${HELPER:-$(dirname "$(readlink -f "$0")")/atlas-helper.py}
  top=$(cd "${cwd:-.}" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null)
  if [ -n "$top" ]; then
    stale=$(timeout 20 "$helper" stale "$top" 2>/dev/null | jq -r '(.stale // []) | map("\(.id) (\(.why))") | join("; ")' 2>/dev/null)
    # The helper caches the atlas for minutes, so a "stale" verdict may predate a refresh made by any session; confirm it uncached.
    if [ -n "$stale" ]; then
      stale=$(ATLAS_CACHE_TTL=0 timeout 20 "$helper" stale "$top" 2>/dev/null | jq -r '(.stale // []) | map("\(.id) (\(.why))") | join("; ")' 2>/dev/null)
    fi
    if [ -n "$stale" ]; then
      jq -n --arg s "$stale" '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny",
        permissionDecisionReason: ("Feature atlas is stale for this branch: " + $s + ". Update those subsystem comments and stamp Verified at with the tip, then push.")}}'
      exit 0
    fi
  fi
  jq -n --arg c "$cmd" '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "ask",
    permissionDecisionReason: ("git push needs explicit confirmation (branch + remote): " + $c)}}'
fi
exit 0
