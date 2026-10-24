#!/usr/bin/env bash
# PreToolUse(Edit|Write|MultiEdit|NotebookEdit): warn, never block, when the file being edited is
# inside the claimed paths of another live Dibs claim. The claim list comes from Dibs itself
# (todo:agent:claims), skipping this session's own claims by conversation id.
# DIBS_CLAIMS_CMD overrides the command (tests); it receives --path=... --except-session=... appended.
input=$(cat)
file=$(jq -r '.tool_input.file_path // .tool_input.notebook_path // empty' <<<"$input")
[ -n "$file" ] || exit 0
session=$(jq -r '.session_id // empty' <<<"$input")

warn() {
  jq -n --arg m "$1" '{hookSpecificOutput: {hookEventName: "PreToolUse", additionalContext: $m}}'
  exit 0
}

read -r -a cmd <<<"${DIBS_CLAIMS_CMD:-docker exec -u www-data dibs-app php artisan todo:agent:claims}"
out=$(timeout 8 "${cmd[@]}" --path="$file" ${session:+--except-session="$session"} 2>/dev/null) \
  || warn "Dibs claim-overlap check skipped (Dibs unreachable or errored); check todo_claim_status before editing $file."

count=$(jq 'length' <<<"$out" 2>/dev/null) || warn "Dibs claim-overlap check skipped (unreadable answer); check todo_claim_status before editing $file."
[ "$count" -gt 0 ] || exit 0
warn "Another live Dibs claim covers $file: $(jq -r 'map("task \(.issueId) held by \(.agentName) on \(.paths | join(", "))") | join("; ")' <<<"$out"). Coordinate (sessioneer --peers / --send) before editing."
