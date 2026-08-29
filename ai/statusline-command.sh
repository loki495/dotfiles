#!/usr/bin/env bash
# >>> claude-session-manager: capture stdin for session-id marker (managed, safe to delete) >>>
csm_statusline_input=$(cat)
exec 0<<< "$csm_statusline_input"
# <<< claude-session-manager: capture stdin <<<
input=$(cat)
cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // ""')
model=$(echo "$input" | jq -r '.model.display_name // ""')
used=$(echo "$input" | jq -r '.context_window.used_percentage // empty')

user=$(whoami)
host=$(hostname -s)
home="$HOME"
display_cwd="${cwd/#$home/~}"

branch=$(git -C "$cwd" --no-optional-locks symbolic-ref --short HEAD 2>/dev/null)

# user@host in bold red, matching starship style
printf "\033[1;31m%s\033[0m@\033[2;31m%s\033[0m" "$user" "$host"

# directory in purple
printf " \033[0;35m%s\033[0m" "$display_cwd"

# git branch in #70aff5 (starship git_branch color) if inside a repo
if [ -n "$branch" ]; then
  printf " \033[38;2;112;175;245m(%s)\033[0m" "$branch"
fi

# model name
printf " | %s" "$model"

# context window usage (only shown after first API response)
if [ -n "$used" ]; then
  printf " | ctx: %.0f%%" "$used"
fi

# claude.ai account quota usage (5-hour window / 7-day rolling)
five=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty')
week=$(echo "$input" | jq -r '.rate_limits.seven_day.used_percentage // empty')
five_reset=$(echo "$input" | jq -r '.rate_limits.five_hour.resets_at // empty')
week_reset=$(echo "$input" | jq -r '.rate_limits.seven_day.resets_at // empty')

now=$(date +%s)

fmt_remaining() {
  local diff=$(( $1 - now ))
  if [ "$diff" -le 0 ]; then
    echo "now"
  elif [ "$diff" -ge 86400 ]; then
    printf '%dd %dh' $(( diff / 86400 )) $(( (diff % 86400) / 3600 ))
  else
    printf '%dh %dm' $(( diff / 3600 )) $(( (diff % 3600) / 60 ))
  fi
}

if [ -n "$five" ] || [ -n "$week" ]; then
  printf " |"
  if [ -n "$five" ]; then
    printf " 5h: %.0f%%" "$five"
    [ -n "$five_reset" ] && printf " (%s)" "$(fmt_remaining "$five_reset")"
  fi
  [ -n "$five" ] && [ -n "$week" ] && printf " |"
  if [ -n "$week" ]; then
    printf " 7d: %.0f%%" "$week"
    [ -n "$week_reset" ] && printf " (%s)" "$(fmt_remaining "$week_reset")"
  fi
fi

echo ""

# >>> claude-session-manager: session-id marker (managed, safe to delete) >>>
csm_json=$(printf '%s' "$csm_statusline_input" | jq -c '{session_id: .session_id, ctx_pct: .context_window.used_percentage, git_worktree: (.workspace.git_worktree // .worktree.name)} | with_entries(select(.value != null))' 2>/dev/null)
[ -n "$csm_json" ] && [ "$csm_json" != "{}" ] && printf "\033[2mcsm-data:%s\033[0m\n" "$csm_json"
# <<< claude-session-manager: session-id marker <<<

# >>> claude-session-manager: quota state capture (managed, safe to delete) >>>
csm_quota_new=$(printf '%s' "$csm_statusline_input" | jq -c '{five_hour: .rate_limits.five_hour, seven_day: .rate_limits.seven_day} | with_entries(select(.value != null))' 2>/dev/null)
if [ -n "$csm_quota_new" ] && [ "$csm_quota_new" != "{}" ]; then
  printf '%s' "$csm_quota_new" | php /home/andres/www/claude-session-manager/host-agent/quota_live_state_write.php >/dev/null 2>&1
fi
# <<< claude-session-manager: quota state capture <<<
