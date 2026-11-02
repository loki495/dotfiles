#!/usr/bin/env python3
"""PreToolUse(todo_show, todo_claim_status): warn, never block, when this is the second or later
single-id call since the last user turn. Each such call costs a model round trip; the ids[] /
issueIds[] forms read many records at once. BATCH_READ_WARN=off disables it."""
import json
import os
import sys

TOOLS = {'mcp__dibs__todo_show': ('id', 'ids'), 'mcp__dibs__todo_claim_status': ('issueId', 'issueIds')}
TAIL_BYTES = 400_000


def is_user_turn(entry):
    if entry.get('type') != 'user' or entry.get('isMeta'):
        return False
    content = entry.get('message', {}).get('content')
    if isinstance(content, str):
        return True
    return isinstance(content, list) and not any(b.get('type') == 'tool_result' for b in content if isinstance(b, dict))


def singles_since_user_turn(path):
    with open(path, 'rb') as fh:
        fh.seek(0, os.SEEK_END)
        fh.seek(max(0, fh.tell() - TAIL_BYTES))
        lines = fh.read().decode('utf-8', 'replace').splitlines()[1:]
    count = 0
    for raw in reversed(lines):
        try:
            entry = json.loads(raw)
        except ValueError:
            continue
        if is_user_turn(entry):
            break
        content = entry.get('message', {}).get('content')
        for block in content if entry.get('type') == 'assistant' and isinstance(content, list) else []:
            single, _ = TOOLS.get(block.get('name'), (None, None))
            if single and single in block.get('input', {}):
                count += 1
    return count


def main():
    if os.environ.get('BATCH_READ_WARN') == 'off':
        return
    data = json.load(sys.stdin)
    single, plural = TOOLS.get(data.get('tool_name'), (None, None))
    if not single or single not in data.get('tool_input', {}):
        return
    path = data.get('transcript_path')
    if not path or not os.path.isfile(path) or singles_since_user_turn(path) < 1:
        return
    print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'additionalContext':
        f'Batch the reads: this is another single-id call without a user turn between. '
        f'Pass {plural}: [...] to read several records in one call.'}}))


if __name__ == '__main__':
    main()
