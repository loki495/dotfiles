#!/usr/bin/env bash
# PreToolUse(Bash): any git push must go through an explicit permission prompt,
# even when allow rules or the permission mode would otherwise let it run silently.
# Every push also lists the unpushed commits (base from @{push}/@{upstream}, as of the last fetch) and risky flags,
# to Andres (the prompt) and to the model (additionalContext).
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
  list=
  if [ -n "$top" ]; then
    base=$(cd "$top" && { git rev-parse --abbrev-ref '@{push}' || git rev-parse --abbrev-ref '@{upstream}'; } 2>/dev/null | head -1)
    if [ -n "$base" ]; then
      log=$(cd "$top" && git log --oneline "$base..HEAD" 2>/dev/null)
      list="Unpushed commits ($base..HEAD, as of last fetch):"$'\n'"${log:-(none)}"
    else
      list="No upstream is configured, so the unpushed commits are unknown."
    fi
  fi
  risky=$(grep -oP '(?<!\S)(--force-with-lease\S*|--force|-f|--delete|-d|--no-verify|--mirror|:\S+)(?=\s|$)' <<<"$cmd" | paste -sd, -)
  [ -n "$risky" ] && list="$list"$'\n'"Risky flags: $risky"
  jq -n --arg c "$cmd" --arg s "$stale" --arg l "$list" '
    ("git push needs explicit confirmation (branch + remote): " + $c +
      (if $l != "" then "\n" + $l else "" end) +
      (if $s != "" then "\nFeature atlas stale for: " + $s + ". A background job refreshes it; do not refresh it in this session (write an atlas hint instead)." else "" end)) as $m
    | {hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "ask", permissionDecisionReason: $m, additionalContext: $m}}'
fi
exit 0
