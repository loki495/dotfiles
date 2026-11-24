"""Lesson channel for rule-inject: pick the active lessons an event is about from a local cache.

The cache ($LESSON_CACHE, default ~/.cache/dibs-lessons.json) is written by ai/scripts/lessons-export.py
from Dibs lesson records; this module only reads it, so a hook call never waits on Dibs. A stale or
missing cache starts a detached refresh. Every failure returns "nothing": the hook must never block.
"""
import json
import os
import re
import shlex
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.realpath(__file__))
EXPORTER = os.path.join(os.path.dirname(HERE), "scripts", "lessons-export.py")
DEFAULT_CACHE = "~/.cache/dibs-lessons.json"
DEFAULT_CAP, DEFAULT_TTL, SUMMARY_MAX = 5, 3600, 120
HEADER = "Lessons for this action:"


def cache_path():
    return os.path.expanduser(os.environ.get("LESSON_CACHE") or DEFAULT_CACHE)


def _int_env(name, default):
    try:
        return max(int(os.environ.get(name, default)), 0)
    except ValueError:
        return default


def load_cache():
    """(generated epoch or None, [valid lesson dicts]); a bad file or entry is skipped."""
    try:
        data = json.load(open(cache_path()))
        entries = data["lessons"]
        generated = data.get("generated")
    except (OSError, ValueError, KeyError, TypeError):
        return None, []
    if not isinstance(entries, list):
        return None, []
    out = []
    for e in entries:
        if (isinstance(e, dict) and isinstance(e.get("id"), int) and not isinstance(e["id"], bool)
                and isinstance(e.get("summary"), str) and e["summary"].strip()
                and isinstance(e.get("triggers"), list) and not e.get("draft")):
            out.append(e)
    ok = isinstance(generated, (int, float)) and not isinstance(generated, bool)
    return (generated if ok else None), out


def refresh_if_stale(generated):
    """Start the exporter detached when the cache is missing or older than LESSON_TTL; never waits."""
    if os.environ.get("LESSON_REFRESH") == "off":
        return
    if generated is not None and time.time() - generated < _int_env("LESSON_TTL", DEFAULT_TTL):
        return
    try:
        cmd = shlex.split(os.environ["LESSON_REFRESH_CMD"]) if os.environ.get("LESSON_REFRESH_CMD") \
            else [sys.executable, EXPORTER]
        subprocess.Popen(cmd, start_new_session=True, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (OSError, ValueError):
        pass


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def _rank(entry, project_parts):
    hits = entry.get("hits") if isinstance(entry.get("hits"), int) and not isinstance(entry.get("hits"), bool) else 0
    last = entry.get("last_seen") if isinstance(entry.get("last_seen"), str) else ""
    local = bool(_norm(entry.get("group", "")) and _norm(entry.get("group", "")) in project_parts)
    # newest date first: invert by comparing on a descending sort of the string, ids ascending last
    return (not local, -hits, _desc(last), entry["id"])


def _desc(date):
    return tuple(-ord(c) for c in date)


def pick(keys, cwd, have):
    """The lessons to deliver now: [(id, one-line text)], at most LESSON_CAP, none already in `have`."""
    wanted = {str(k).replace("-", " ") for k in keys}
    if not wanted:
        return []
    generated, entries = load_cache()
    refresh_if_stale(generated)
    parts = {_norm(p) for p in str(cwd or "").split("/")} - {""}
    eligible = [e for e in entries
                if wanted & {t for t in e["triggers"] if isinstance(t, str)} and f"lesson:{e['id']}" not in have]
    eligible.sort(key=lambda e: _rank(e, parts))
    out = []
    for e in eligible[:_int_env("LESSON_CAP", DEFAULT_CAP)]:
        text = re.sub(r"\s+", " ", e["summary"]).strip()[:SUMMARY_MAX]
        out.append((e["id"], f"[lesson {e['id']}] {text}"))
    return out
