#!/usr/bin/env bash
# PreToolUse(Read): deny a whole-file Read of a large text file so the model greps/LSPs first and
# reads only the part it needs. Passing offset/limit (or allow_large) gets through on the re-run.
# READ_GUARD_LINES sets the threshold (default 400); READ_GUARD=off disables it.
[ "${READ_GUARD:-on}" = off ] && exit 0
input=$(cat)
file=$(jq -r '.tool_input.file_path // empty' <<<"$input")
[ -n "$file" ] && [ -f "$file" ] || exit 0
[ "$(jq -r '(.tool_input.offset // .tool_input.limit // .tool_input.pages // .tool_input.allow_large // false) | tostring' <<<"$input")" = false ] || exit 0
case "${file,,}" in
  *.png|*.jpg|*.jpeg|*.gif|*.webp|*.bmp|*.svg|*.pdf|*.ipynb) exit 0 ;;
esac
max=${READ_GUARD_LINES:-400}
lines=$(wc -l <"$file" 2>/dev/null) || exit 0
[ "$lines" -gt "$max" ] || exit 0
jq -n --arg m "$file has $lines lines (over $max). Find the relevant part first (Grep, LSP, or grep -n), then Read it with offset/limit. If you truly need the whole file, re-run with limit set to $lines." \
  '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $m}}'
