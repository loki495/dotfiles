#!/usr/bin/env python3
"""Token usage per day/week from Claude Code transcripts (report only, always exits 0).

Usage: token-usage.py [--days 28] [--projects-dir DIR] [--ctx-limit 250000]
See ai/scripts/README.md.
"""
import argparse
import collections
import datetime
import glob
import json
import os

CTX_LIMIT = 250_000
BAR = 30


def read_turns(projects_dir, since):
    """Yield (ts, session, ctx, output, cache_read, cache_write, input) once per API message."""
    seen = {}
    for path in glob.glob(os.path.join(projects_dir, '*', '**', '*.jsonl'), recursive=True):
        rel = os.path.relpath(path, projects_dir).split(os.sep)
        session = rel[1] if len(rel) > 2 else os.path.splitext(rel[1])[0]
        try:
            if os.path.getmtime(path) < since.timestamp():
                continue
            lines = open(path, encoding='utf-8', errors='replace').read().splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                e = json.loads(line)
                m = e['message']
                u = m['usage']
                ts = datetime.datetime.fromisoformat(e['timestamp'].replace('Z', '+00:00'))
            except (ValueError, KeyError, TypeError, AttributeError):
                continue
            if e.get('type') != 'assistant' or ts < since or not m.get('id'):
                continue
            row = (ts, session, u.get('input_tokens') or 0, u.get('cache_read_input_tokens') or 0,
                   u.get('cache_creation_input_tokens') or 0, u.get('output_tokens') or 0)
            old = seen.get(m['id'])
            # a response is split across entries; only the last carries the final output_tokens
            if old is None or row[5] > old[5]:
                seen[m['id']] = row
    return seen.values()


def aggregate(turns, key, ctx_limit):
    buckets = collections.defaultdict(lambda: {'sessions': set(), 'turns': 0, 'over': 0,
                                               'read': 0, 'write': 0, 'in': 0, 'out': 0})
    for ts, session, inp, read, write, out in turns:
        b = buckets[key(ts)]
        b['sessions'].add(session)
        b['turns'] += 1
        b['over'] += inp + read + write > ctx_limit
        b['read'] += read
        b['write'] += write
        b['in'] += inp
        b['out'] += out
    return dict(sorted(buckets.items()))


def fmt(n):
    for unit, div in (('B', 1e9), ('M', 1e6), ('k', 1e3)):
        if n >= div:
            return f'{n / div:.1f}{unit}'
    return str(int(n))


def render(title, buckets, delta=False):
    if not buckets:
        return f'{title}\n  (no transcripts in range)\n'
    total = lambda b: b['read'] + b['write'] + b['in'] + b['out']
    peak = max(total(b) for b in buckets.values()) or 1
    out = [title, f'  {"":10} {"sess":>4} {"turns":>6} {"total":>7} {"tok/sess":>8} {"cache%":>6} {"turns>ctx":>9}'
           + (f' {"Δtok/sess":>9} {"Δctx":>6}' if delta else '')]
    prev = None
    for k, b in buckets.items():
        t, n = total(b), len(b['sessions'])
        cache = 100 * b['read'] / t if t else 0
        over = 100 * b['over'] / b['turns']
        bar = '█' * round(BAR * t / peak)
        d = ''
        if delta:
            d = ' ' + (f'{100 * (t / n / prev[0] - 1):>+8.0f}% {over - prev[1]:>+5.0f}pp' if prev else f'{"":>9} {"":>6}')
            prev = (t / n, over)
        out.append(f'  {k:10} {n:>4} {b["turns"]:>6} {fmt(t):>7} {fmt(t / n):>8} {cache:>5.0f}% {over:>8.0f}%{d}  {bar}')
    return '\n'.join(out) + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--days', type=int, default=28)
    ap.add_argument('--projects-dir', default=os.path.expanduser('~/.claude/projects'))
    ap.add_argument('--ctx-limit', type=int, default=CTX_LIMIT)
    a = ap.parse_args()
    since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=a.days)
    turns = list(read_turns(a.projects_dir, since))
    day = lambda ts: ts.astimezone().strftime('%Y-%m-%d')
    week = lambda ts: ts.astimezone().strftime('%G-W%V')
    print(render(f'Per day (last {a.days}d; turns>ctx = share of turns over {fmt(a.ctx_limit)} context)',
                 aggregate(turns, day, a.ctx_limit)))
    print(render('Per week (Δ = change vs the previous week; ctx in percentage points)', aggregate(turns, week, a.ctx_limit), delta=True))


if __name__ == '__main__':
    main()
