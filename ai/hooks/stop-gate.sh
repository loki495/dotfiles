#!/usr/bin/env bash
# Stop: block ending a turn whose last 3 non-empty lines lack the rule-1226 status line (one of the fixed
# phrases), once per turn (stop_hook_active), failing open when the message is absent.
# Check status before bookkeeping; completion statuses require claims to be released or completed.
# A repeated stop allows with a warning. DIBS_STOP_GATE=off skips the gate; Dibs outages warn and allow.
# A session whose exact cwd is registered in STOP_GATE_SKIP_DIR (fresh, user-owned entry) is skipped entirely.
# DIBS_CLAIMS_CMD overrides the command (tests); it receives --held-by=<session id> appended.
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
[ "$count" -gt 0 ] || { [ -n "$block_msg" ] && jq -n --arg m "$block_msg" '{systemMessage: $m}'; exit 0; }

held=$(jq -r 'map("task \(.issueId)") | join(", ")' <<<"$out")
case "$status" in
  'Continue in this session:'|'Waiting on Andres:'|'Waiting on other work:')
    [ -n "$block_msg" ] && jq -n --arg m "$block_msg" '{systemMessage: $m}'
    exit 0 ;;
esac
if [ "$active" = true ]; then
  warn "Stopped while holding a Dibs claim ($held); release or complete it."
fi
if [ "$status" = 'Continue in a different session:' ]; then
  reason="This session holds $held. File a handoff as one temporary task labelled handoff with the session-handoff skill, give Andres its id, then release with todo_release and a handoff."
else
  reason="This session holds $held. Output [complete <id> | sha=... tests=\"...\" | notes] or release with todo_release and a comment saying what is left."
fi
jq -n --arg r "$reason" '{decision: "block", reason: $r}'
