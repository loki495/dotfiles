#!/usr/bin/env bash
# Stop: block ending a turn whose last 3 non-empty lines lack the rule-1226 status line (one of the fixed
# phrases), once per turn (stop_hook_active), failing open when the message is absent.
# Check status before bookkeeping; completion statuses require claims to be released or completed.
# A repeated stop allows with a warning. DIBS_STOP_GATE=off skips the gate; Dibs outages warn and allow.
# A session whose exact cwd is registered in STOP_GATE_SKIP_DIR (fresh, user-owned entry) is skipped entirely.
# DIBS_CLAIMS_CMD overrides the command (tests); it receives --held-by=<session id> appended.
# Lesson check: the first completion status of a session whose transcript shows work (an edit, a Dibs claim or
# completion, a failed tool call) asks once for a draft lesson. Marker in STOP_GATE_STATE_DIR; if it cannot be
# written nothing is asked. DIBS_LESSON_PROMPT=off disables it.
input=$(cat)
# One-off sessions that must return exactly what they were asked (e.g. a bridge extraction) opt out by
# registering their exact working directory in a private runtime dir, never inside the directory itself
# (a repo cannot ship the opt-out). The entry must be owned by this user and touched in the last 30 minutes.
cwd=$(jq -r '.cwd // empty' <<<"$input")
if [ -n "$cwd" ]; then
  skip="${STOP_GATE_SKIP_DIR:-${XDG_RUNTIME_DIR:-$HOME/.cache}/dibs-stop-gate-skip}/$(printf %s "$cwd" | sha256sum | cut -c1-32)"
  [ -f "$skip" ] && [ -O "$skip" ] && [ -n "$(find "$skip" -mmin -30 2>/dev/null)" ] && exit 0
fi
session=$(jq -r '.session_id // empty' <<<"$input")
msg=$(jq -r '.last_assistant_message // empty' <<<"$input")
active=$(jq -r '.stop_hook_active // false' <<<"$input")
tail3=$(grep -v '^[[:space:]]*$' <<<"$msg" | tail -n 3)
status=$(grep -oE 'Safe to archive this session\.|Continue in this session:|Continue in a different session:|Waiting on (Andres|other work):|All planned work is done\.' <<<"$tail3" | tail -n 1)
if [ "${DIBS_STOP_GATE:-}" != off ] && [ -n "$session" ] && [ -n "$msg" ] && [ -z "$status" ] && [ "$active" != true ]; then
  jq -n '{decision: "block", reason: "Rule 1226: output only the missing status line. If waiting on the user, ask it with AskUserQuestion first. If you handed this session over, use Safe to archive. If your message included a dibs block or [complete ...] line, repeat those lines too."}'
  exit 0
fi
block=$("${DIBS_BLOCK_CMD:-$(dirname "$0")/dibs-block.py}" stop <<<"$input" 2>/dev/null)
if [ "$(jq -r '.decision // empty' <<<"$block" 2>/dev/null)" = block ]; then
  printf '%s\n' "$block"
  exit 0
fi
block_msg=$(jq -r '.systemMessage // empty' <<<"$block" 2>/dev/null)
[ "${DIBS_STOP_GATE:-}" = off ] && { [ -n "$block_msg" ] && jq -n --arg m "$block_msg" '{systemMessage: $m}'; exit 0; }
[ -n "$session" ] || exit 0

warn() {
  jq -n --arg m "${block_msg:+$block_msg | }$1" '{systemMessage: $m}'
  exit 0
}

read -r -a cmd <<<"${DIBS_CLAIMS_CMD:-docker exec -u www-data dibs-app php artisan todo:agent:claims}"
out=$(timeout 8 "${cmd[@]}" --held-by="$session" 2>/dev/null) \
  || warn "Stop gate skipped: Dibs unreachable or errored, so open claims were not checked."
count=$(jq 'length' <<<"$out" 2>/dev/null) \
  || warn "Stop gate skipped: unreadable answer from Dibs, so open claims were not checked."
held=$(jq -r 'map("task \(.issueId)") | join(", ")' <<<"$out")

# Idle, unarchived sessions this session launched. Only completion statuses care; an unreachable or refused
# lookup (no tracked caller, host agent down) adds nothing so the gate never blocks on missing data.
idle=""
case "$status" in
  'Safe to archive this session.'|'All planned work is done.')
    read -r -a scmd <<<"${SESSIONEER_SPAWNED_CMD:-sessioneer --spawned --json}"
    sout=$(timeout 8 "${scmd[@]}" 2>/dev/null) || sout=""
    idle=$(jq -r 'if .ok == true then [.sessions[]? | select(.status == "idle" and (.archived // false) != true) | .name] | join(", ") else "" end' <<<"$sout" 2>/dev/null) || idle="" ;;
esac

case "$status" in
  'Continue in this session:'|'Waiting on Andres:'|'Waiting on other work:')
    [ -n "$block_msg" ] && jq -n --arg m "$block_msg" '{systemMessage: $m}'
    exit 0 ;;
esac

# True at most once per session: claiming the marker is part of the test, so ask only when about to block.
lesson_due() {
  [ "${DIBS_LESSON_PROMPT:-}" != off ] && [ -n "$status" ] || return 1
  local transcript dir marker
  transcript=$(jq -r '.transcript_path // empty' <<<"$input")
  [ -f "$transcript" ] && [ -r "$transcript" ] || return 1
  dir=${STOP_GATE_STATE_DIR:-${XDG_RUNTIME_DIR:-$HOME/.cache}/dibs-stop-gate}
  marker="$dir/lesson-$(printf %s "$session" | tr -c 'A-Za-z0-9_-' _)"
  [ ! -e "$marker" ] || return 1
  grep -qE '"name":"(Edit|Write|MultiEdit|NotebookEdit|mcp__dibs__todo_claim|mcp__dibs__todo_complete)"|"is_error":true' "$transcript" || return 1
  mkdir -p "$dir" 2>/dev/null && : 2>/dev/null >"$marker"
}
lesson="Lesson check (asked once per session): did an error, a correction, a blocked or failed action, or a better way come up that would prevent a repeat? If yes, search Dibs first (todo_search, one or two keywords, then a synonym, open and closed); add a recurrence comment to a match, else file a draft with todo_create: title 'Lesson: <do or avoid>', labels lesson, draft and fitting 'trigger <key>' labels, an idempotency key, the project's Area and Group, and body lines Summary (max 120 characters), Symptom, Cause, Do instead, Evidence, Confidence, Hits and Last seen, Expires (Dibs guide 2272). Keep the draft label and mention the id. Skip one-off facts that code or git history already record. If there is nothing, say 'No lesson to file.' Then end with your status line again, repeating any dibs block or [complete] line"

if [ "$count" -eq 0 ] && [ -z "$idle" ]; then
  if lesson_due; then
    jq -n --arg r "$lesson." --arg m "$block_msg" '{decision: "block", reason: $r} + (if $m == "" then {} else {systemMessage: $m} end)'
    exit 0
  fi
  [ -n "$block_msg" ] && jq -n --arg m "$block_msg" '{systemMessage: $m}'
  exit 0
fi

parts=()
[ "$count" -gt 0 ] && parts+=("holds $held")
[ -n "$idle" ] && parts+=("has idle sessions it launched that are not archived ($idle)")
problem=$(IFS=';'; printf '%s' "${parts[*]}" | sed 's/;/ and /')
if [ "$active" = true ]; then
  warn "Stopped while this session $problem; release, complete or archive them."
fi
steps=()
if [ "$status" = 'Continue in a different session:' ]; then
  [ "$count" -gt 0 ] && steps+=("file a handoff as one temporary task labelled handoff with the session-handoff skill, give Andres its id, then release with todo_release and a handoff")
else
  [ "$count" -gt 0 ] && steps+=("output [complete <id> | sha=... tests=\"...\" | notes] or release with todo_release and a comment saying what is left")
fi
[ -n "$idle" ] && steps+=("run sessioneer --reap to archive the idle claim-free ones, or archive them as the session-flow skill describes")
reason="This session $problem. Fix everything in one pass: $(IFS=';'; printf '%s' "${steps[*]}" | sed 's/;/; and /')."
lesson_due && reason="$reason Also, $lesson."
jq -n --arg r "$reason" '{decision: "block", reason: $r}'
