#!/usr/bin/env bash
# Stop: block ending a turn whose last 3 non-empty lines lack the rule-1226 status line (one of the fixed
# phrases), once per turn (stop_hook_active), failing open when the message is absent.
# Also block ending the session while it still holds a live Dibs claim. Blocks at most
# STOP_GATE_CAP times per session (a counter file), then allows with a visible warning, so it can
# never loop. DIBS_STOP_GATE=off skips the gate. Dibs unreachable allows with a warning.
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
# The ```dibs block is applied first (idempotent), so a done line closes its claim before the
# claim check below, and a block re-sent after a status-line block is not lost or doubled.
block=$("${DIBS_BLOCK_CMD:-$(dirname "$0")/dibs-block.py}" stop <<<"$input" 2>/dev/null)
if [ "$(jq -r '.decision // empty' <<<"$block" 2>/dev/null)" = block ]; then
  printf '%s\n' "$block"
  exit 0
fi
block_msg=$(jq -r '.systemMessage // empty' <<<"$block" 2>/dev/null)
[ "${DIBS_STOP_GATE:-}" = off ] && { [ -n "$block_msg" ] && jq -n --arg m "$block_msg" '{systemMessage: $m}'; exit 0; }
session=$(jq -r '.session_id // empty' <<<"$input")
[ -n "$session" ] || exit 0

msg=$(jq -r '.last_assistant_message // empty' <<<"$input")
tail3=$(grep -v '^[[:space:]]*$' <<<"$msg" | tail -n 3)
if [ -n "$msg" ] && [ "$(jq -r '.stop_hook_active // false' <<<"$input")" != true ] \
  && ! grep -q -E 'Safe to archive this session\.|Continue in this session:|Continue in a different session:|Waiting on (Andres|other work):|All planned work is done\.' <<<"$tail3"; then
  jq -n '{decision: "block", reason: "Rule 1226: end your message with one status line, exactly one of: \"Safe to archive this session.\" / \"Continue in this session: <what and why>.\" / \"Continue in a different session: <which session or agent, and why>.\" / \"Waiting on Andres: <input needed>.\" / \"Waiting on other work: <what>.\" / \"All planned work is done.\" (archive only after claims are released and records updated). If you handed this session over to a new session or a handoff that does not need this one, the line is \"Safe to archive this session.\" naming the new session, never \"Waiting on other work\". If you are waiting on the user for a decision or answer from this session, ask it with AskUserQuestion first (explanation, recommended option first); use the Waiting on Andres line only for what a question cannot carry (a real-world action, a file to review, a later date). You need not repeat the whole message: if nothing else changed, output only the missing status line; resend the full message only if something else changed."}'
  exit 0
fi

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
