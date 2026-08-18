#!/bin/sh
# Called by hypridle's suspend listener once the idle timeout is hit. If a
# Claude Code session is actively working (tracked by
# ~/.claude/scripts/track-activity.sh via its UserPromptSubmit/PreToolUse/Stop
# hooks), waits for it to finish before actually suspending. hypridle's
# on-resume kills this script if the user returns first, so a finished
# Claude session doesn't trigger a belated suspend after the user is back.
#
# Prunes stale locks itself on every poll (unlike track-activity.sh's own
# crash-safety prune, which only runs when some session's hooks happen to
# fire). Without this, a lock orphaned by a session that crashed without
# firing Stop could block suspend indefinitely whenever nobody else's hooks
# fire either -- e.g. overnight with no active session at all (confirmed
# live 2026-08-18). Safe to use a much shorter threshold than
# track-activity.sh's 3h, because PreToolUse now refreshes an active
# session's lock on every tool call, so genuinely active sessions (even long
# single turns) stay fresh well within it.
ACTIVE_DIR="$HOME/.claude/inhibit/active"
STALE_SECONDS=1200 # 20min.

any_active() {
    now=$(date +%s)
    for f in "$ACTIVE_DIR"/*.lock; do
        [ -e "$f" ] || continue
        mtime=$(stat -c %Y "$f" 2>/dev/null || echo "$now")
        if [ $(( now - mtime )) -gt "$STALE_SECONDS" ]; then
            rm -f "$f"
        else
            return 0
        fi
    done
    return 1
}

while any_active; do
    sleep 30
done
systemctl suspend
