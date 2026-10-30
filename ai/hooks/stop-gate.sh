#!/usr/bin/env bash
# Stop: block ending the session while it still holds a live Dibs claim. Blocks at most
# STOP_GATE_CAP times per session (a counter file), then allows with a visible warning, so it can
# never loop. DIBS_STOP_GATE=off skips the gate. Dibs unreachable allows with a warning.
# DIBS_CLAIMS_CMD overrides the command (tests); it receives --held-by=<session id> appended.
input=$(cat)
[ "${DIBS_STOP_GATE:-}" = off ] && exit 0
session=$(jq -r '.session_id // empty' <<<"$input")
[ -n "$session" ] || exit 0

warn() {
  jq -n --arg m "$1" '{systemMessage: $m}'
  exit 0
}

read -r -a cmd <<<"${DIBS_CLAIMS_CMD:-docker exec -u www-data dibs-app php artisan todo:agent:claims}"
out=$(timeout 8 "${cmd[@]}" --held-by="$session" 2>/dev/null) \
  || warn "Stop gate skipped: Dibs unreachable or errored, so open claims were not checked."
count=$(jq 'length' <<<"$out" 2>/dev/null) \
  || warn "Stop gate skipped: unreadable answer from Dibs, so open claims were not checked."
[ "$count" -gt 0 ] || exit 0

held=$(jq -r 'map("task \(.issueId)") | join(", ")' <<<"$out")
cap=${STOP_GATE_CAP:-2}
dir=${STOP_GATE_STATE_DIR:-${XDG_RUNTIME_DIR:-$HOME/.cache}/dibs-stop-gate}
(umask 077; mkdir -p "$dir")
file="$dir/${session//[^A-Za-z0-9_-]/_}"
blocks=$(cat "$file" 2>/dev/null || echo 0)
[[ $blocks =~ ^[0-9]+$ ]] || blocks=0
if [ "$blocks" -ge "$cap" ]; then
  warn "Stopped while holding a Dibs claim ($held); the stop gate's block cap ($cap) was reached. Release or complete it from the next session, and file a handoff task for any unfinished work."
fi
echo $((blocks + 1)) >"$file"
jq -n --arg r "This session still holds a live Dibs claim ($held). Complete it (todo_complete) or release it (todo_release, with a comment on what is left and the next step) before ending. If the work is unfinished, file the handoff first: one temporary Dibs task labelled handoff, body from skill session-handoff, and give Andres its id. Block $((blocks + 1)) of $cap; set DIBS_STOP_GATE=off to skip this gate." \
  '{decision: "block", reason: $r}'
