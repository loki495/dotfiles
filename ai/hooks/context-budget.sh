#!/usr/bin/env bash
# UserPromptSubmit: every call re-reads the whole context, and a prompt sent after the
# prompt cache expired rewrites all of it at cache-write price. So:
#  - idle past the cache TTL with a big context: block the prompt once (re-send to go on),
#    so the choice between paying the rewrite and /handoff + /clear is deliberate;
#  - context over budget: tell Claude to offer /handoff + /clear, and show a warning.
# Slash commands pass through untouched so /handoff, /clear etc. always work.
budget=${CLAUDE_CTX_BUDGET:-250000}
idle_min=${CLAUDE_CTX_IDLE_MIN:-60}
idle_floor=${CLAUDE_CTX_IDLE_FLOOR:-100000}

in=$(cat)
prompt=$(jq -r '.prompt // ""' <<<"$in")
[[ $prompt == /* ]] && exit 0
transcript=$(jq -r '.transcript_path // ""' <<<"$in")
session=$(jq -r '.session_id // "unknown"' <<<"$in")
[[ -f $transcript ]] || exit 0

marker_dir=${XDG_RUNTIME_DIR:-/tmp}/claude-context-budget
marker=$marker_dir/$session
mkdir -p "$marker_dir"

# Relies on the transcript format (assistant entries carrying .message.usage and
# .timestamp). If a Claude Code update changes it, say so once per session instead of
# silently going inert.
# A compaction (manual, auto or idle) after the last assistant entry has already shrunk
# the context, so it counts instead, at its postTokens, from its own timestamp.
last=$(tac "$transcript" | jq -cn 'first(inputs | select((.type == "assistant" and .message.usage) or (.subtype == "compact_boundary" and .compactMetadata.postTokens)))' 2>/dev/null)
ctx=$(jq -e 'if .subtype == "compact_boundary" then .compactMetadata.postTokens else .message.usage | (.input_tokens // 0) + (.cache_read_input_tokens // 0) + (.cache_creation_input_tokens // 0) end' <<<"$last" 2>/dev/null)
ts=$(jq -r '.timestamp // empty' <<<"$last" 2>/dev/null)
then_s=$(date -d "$ts" +%s 2>/dev/null)
if [[ ! $ctx =~ ^[0-9]+$ || ! $then_s =~ ^[0-9]+$ ]]; then
  # A brand-new session has no assistant entry yet; only complain once one exists.
  if grep -q '"type":"assistant"' "$transcript" && [[ ! -e $marker.broken ]]; then
    touch "$marker.broken"
    jq -n --arg p "$0" '{systemMessage: ("context-budget hook could not read token usage/timestamps from the transcript; the format may have changed in a Claude Code update. Hook is inactive until " + $p + " is fixed.")}'
  fi
  exit 0
fi
idle=$(( ($(date +%s) - then_s) / 60 ))
k=$(( ctx / 1000 ))
if (( idle >= idle_min && ctx >= idle_floor )) && [[ $(cat "$marker" 2>/dev/null) != "$ts" ]]; then
  printf '%s' "$ts" >"$marker"
  jq -n --arg r "Idle ${idle} min with a ${k}k-token context: the prompt cache has likely expired, so this prompt would rewrite all ${k}k tokens. Not sent. Decide whether this context is worth that cost: re-send the same prompt to continue anyway, or start a fresh session from a /handoff. Either way, keep a Dibs task current with the work's state so another session can pick it up." \
    '{decision: "block", reason: $r}'
  exit 0
fi

if (( ctx >= budget )); then
  jq -n --arg m "Context is ${k}k tokens (budget $(( budget / 1000 ))k); every call re-reads all of it." \
    --arg c "Context is ${k}k tokens, over the $(( budget / 1000 ))k budget. Before starting new work, briefly tell the user and offer /handoff then /clear. If mid-task, finish the current step first." \
    '{systemMessage: $m, hookSpecificOutput: {hookEventName: "UserPromptSubmit", additionalContext: $c}}'
fi
exit 0
