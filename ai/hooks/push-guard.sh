#!/usr/bin/env bash
# PreToolUse(Bash): any git push must go through an explicit permission prompt,
# even when allow rules or the permission mode would otherwise let it run silently.
# A push never waits on the atlas: when a subsystem's owned files changed since its Verified at, the
# confirmation prompt says so (a background job refreshes it; sessions do not). Dibs trouble skips that note.
# HELPER overrides the atlas helper (tests).
input=$(cat)
cmd=$(jq -r '.tool_input.command // ""' <<<"$input")
if grep -Eq '(^|[^[:alnum:]_-])git([[:space:]]+-[^[:space:]]+([[:space:]]+[^-[:space:]][^[:space:]]*)?)*[[:space:]]+push([[:space:]]|$)' <<<"$cmd"; then
  cwd=$(jq -r '.cwd // empty' <<<"$input")
  helper=${HELPER:-$(dirname "$(readlink -f "$0")")/atlas-helper.py}
  stale=
  top=$(cd "${cwd:-.}" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null)
  if [ -n "$top" ]; then
    stale=$(timeout 20 "$helper" stale "$top" 2>/dev/null | jq -r '(.stale // []) | map("\(.id) (\(.why))") | join("; ")' 2>/dev/null)
    # The helper caches the atlas for minutes, so a "stale" verdict may predate a refresh made by any session; confirm it uncached.
    if [ -n "$stale" ]; then
      stale=$(ATLAS_CACHE_TTL=0 timeout 20 "$helper" stale "$top" 2>/dev/null | jq -r '(.stale // []) | map("\(.id) (\(.why))") | join("; ")' 2>/dev/null)
    fi
  fi
  jq -n --arg c "$cmd" --arg s "$stale" '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "ask",
    permissionDecisionReason: ("git push needs explicit confirmation (branch + remote): " + $c +
      (if $s != "" then ". Feature atlas stale for: " + $s + ". A background job refreshes it; do not refresh it in this session (write an atlas hint instead)." else "" end))}}'
fi
exit 0
