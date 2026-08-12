#!/bin/sh
# Called by hypridle's suspend listener once the idle timeout is hit. If a
# Claude Code session is actively working (tracked by
# ~/.claude/scripts/track-activity.sh via its UserPromptSubmit/Stop hooks),
# waits for it to finish before actually suspending. hypridle's on-resume
# kills this script if the user returns first, so a finished Claude session
# doesn't trigger a belated suspend after the user is back.
ACTIVE_DIR="$HOME/.claude/inhibit/active"
while [ -n "$(ls -A "$ACTIVE_DIR" 2>/dev/null)" ]; do
    sleep 30
done
systemctl suspend
