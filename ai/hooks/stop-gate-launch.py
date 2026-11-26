#!/usr/bin/env python3
"""Print "missing" when a Claude transcript shows no launch offer: no AskUserQuestion call in the current
turn and no successful sessioneer launch anywhere in the session. Print nothing otherwise, including when
the transcript cannot be read (the stop gate fails open).

Usage: stop-gate-launch.py TRANSCRIPT
"""
import json
import os
import re
import shlex
import sys

SEPARATORS = set(';&|()\n')
PREFIXES = {'env', 'timeout', 'rtk', 'nohup', 'command', 'exec', 'do', 'then', 'else', '{', '-i'}
HEREDOC = re.compile(r"(?<!<)<<(?!<)-?[ \t]*(['\"]?)(\w+)\1([^\n]*)\n.*?^[ \t]*\2[ \t]*$", re.S | re.M)


def commands(text):
    """The simple commands of a shell line as token lists; a quoted prompt stays one token."""
    text = HEREDOC.sub(r'\3', text.replace('\\\n', ' '))
    lex = shlex.shlex(text, posix=True, punctuation_chars=';&|()<>\n')
    lex.whitespace = ' \t\r'
    lex.whitespace_split = True
    words = []
    try:
        for token in lex:
            if set(token) <= SEPARATORS:
                yield words
                words = []
            else:
                words.append(token)
    except ValueError:
        pass
    yield words


def launch_kind(command):
    """'direct' for --rotate or a --workdir launch, 'auto' for --next (launches only if its output says so)."""
    kind = None
    if 'sessioneer' not in command:
        return kind
    for words in commands(command):
        while words and (words[0] in PREFIXES or re.match(r'\w+=|\d+[smh]?$', words[0])):
            words = words[1:]
        if not words or os.path.basename(words[0]) != 'sessioneer':
            continue
        flags = {w.split('=', 1)[0] for w in words[1:] if w.startswith('-')}
        if flags & {'--dry-run', '--help', '-h', '--send', '--offer'}:
            continue
        if flags & {'--rotate', '--workdir'} and '--next' not in flags:
            return 'direct'
        if '--next' in flags:
            kind = 'auto'
    return kind


def blocks(entry):
    content = (entry.get('message') or {}).get('content')
    if isinstance(content, str):
        return [{'type': 'text', 'text': content}]
    return [b for b in content or [] if isinstance(b, dict)]


def starts_turn(entry):
    if entry.get('type') != 'user' or entry.get('isMeta') or entry.get('isCompactSummary'):
        return False
    if (entry.get('origin') or {}).get('kind') == 'task-notification':
        return False
    parts = blocks(entry)
    return bool(parts) and not any(b.get('type') == 'tool_result' for b in parts)


def offer_missing(lines):
    asked = False
    launches = {}
    seen = False
    for line in lines:
        try:
            entry = json.loads(line)
            if entry.get('isSidechain') or entry.get('type') not in ('user', 'assistant'):
                continue
            seen = True
            if starts_turn(entry):
                asked = False
            for block in blocks(entry):
                if block.get('type') == 'tool_use':
                    if block.get('name') == 'AskUserQuestion':
                        asked = True
                    elif block.get('name') == 'Bash':
                        kind = launch_kind(str((block.get('input') or {}).get('command', '')))
                        if kind:
                            launches[block.get('id')] = kind
                elif block.get('type') == 'tool_result' and not block.get('is_error'):
                    kind = launches.get(block.get('tool_use_id'))
                    if kind == 'direct' or (kind == 'auto' and 'auto-continued:' in json.dumps(block.get('content'))):
                        return False
        except (ValueError, AttributeError, TypeError):
            continue
    return seen and not asked


if __name__ == '__main__':
    try:
        with open(sys.argv[1], encoding='utf-8', errors='replace') as transcript:
            if offer_missing(transcript):
                print('missing')
    except (OSError, IndexError):
        pass
