#!/usr/bin/env bash
# Stop: bridge the rule-1226 status line to the flow offer the dashboard shows, without a model turn.
# The reply's last non-blank line picks the intent (done, step-end or wait) and `--post` stores the
# offer, so the dashboard band follows every status line even when the session never asks for a decision.
# Silent and exit 0 on every other shape: no status line, no message, no SESSIONEER_SELF, unreadable
# stdin, a failing or hanging binary. This hook never blocks the turn.
input=$(cat)
msg=$(jq -r '.last_assistant_message // .message // ""' <<<"$input" 2>/dev/null) || exit 0
line=$(grep -v '^[[:space:]]*$' <<<"$msg" | tail -n 1)
line=${line#"${line%%[![:space:]]*}"}
line=${line%"${line##*[![:space:]]}"}
case "$line" in
  'Safe to archive this session.'*|'All planned work is done.'*) intent=done ;;
  'Continue in this session:'*|'Continue in a different session:'*) intent=step-end ;;
  'Waiting on Andres:'*|'Waiting on other work:'*) intent=wait ;;
  *) exit 0 ;;
esac
[ -n "${SESSIONEER_SELF:-}" ] || exit 0
timeout 5 "${SESSIONEER_BIN:-sessioneer}" --next --intent "$intent" --post >/dev/null 2>&1 || true
exit 0
