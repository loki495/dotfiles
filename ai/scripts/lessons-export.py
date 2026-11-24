#!/usr/bin/env python3
"""Export the active Dibs lesson records to the cache the rule-inject hook reads.

A lesson is active when it is OPEN, labelled `lesson`, not labelled `draft`, and carries at least one
`trigger <key>` label (guide: Dibs "Guide: lesson records, states, trigger tags and curation").
The cache ($LESSON_CACHE, default ~/.cache/dibs-lessons.json) holds one entry per lesson:
id, summary (the body's `Summary:` line), triggers (label names without `trigger `), group and area
(the record's project), hits and last_seen (body lines `Hits: N` and `Last seen: YYYY-MM-DD`).
The Dibs CLI prefix is $DIBS_CLI (default `docker exec -u www-data dibs-app php artisan`). When the
list call or any show call fails, the existing cache is left alone and the exit code is 2. A flock
keeps two refreshes from running at once; the second exits 0 without doing anything.

Usage: lessons-export.py
"""
import fcntl
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time

CLI = shlex.split(os.environ.get("DIBS_CLI") or "docker exec -u www-data dibs-app php artisan")
CACHE = os.path.expanduser(os.environ.get("LESSON_CACHE") or "~/.cache/dibs-lessons.json")
TIMEOUT = 30
PREFIX = "trigger "


def cli(cmd, *args):
    r = subprocess.run(CLI + [f"todo:agent:{cmd}", *args], capture_output=True, text=True, timeout=TIMEOUT)
    if r.returncode:
        raise RuntimeError(f"{cmd} exited {r.returncode}")
    return json.loads(r.stdout)


def triggers_of(task):
    labels = task.get("labels") or []
    return [l[len(PREFIX):].strip() for l in labels if isinstance(l, str) and l.startswith(PREFIX) and l[len(PREFIX):].strip()]


def is_active(task):
    labels = task.get("labels") or []
    return (task.get("state") == "OPEN" and "lesson" in labels and "draft" not in labels
            and bool(triggers_of(task)))


def parse_body(body):
    """(summary, hits, last_seen) from a lesson body; summary is None when the line is missing."""
    summary = re.search(r"(?mi)^[ \t]*[-*]?[ \t]*Summary:[ \t]*(\S.*?)[ \t\r]*$", body or "")
    hits = re.search(r"(?i)\bHits:\s*(\d+)", body or "")
    seen = re.search(r"(?i)\bLast seen:\s*(\d{4}-\d{2}-\d{2})", body or "")
    return (summary.group(1) if summary else None, int(hits.group(1)) if hits else 0, seen.group(1) if seen else "")


def entry(task):
    summary, hits, seen = parse_body(cli("show", str(task["id"])).get("body"))
    if not summary:
        return None
    member = (task.get("memberships") or [{}])[0]
    return {"id": task["id"], "summary": summary, "triggers": triggers_of(task),
            "group": member.get("group") or "", "area": member.get("title") or "",
            "hits": hits, "last_seen": seen}


def write_cache(lessons):
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(CACHE), prefix=".lessons-")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump({"generated": time.time(), "lessons": lessons}, f)
        os.replace(tmp, CACHE)
    except BaseException:
        os.path.exists(tmp) and os.remove(tmp)
        raise


def main():
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE + ".lock", "a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return 0
        try:
            tasks = cli("list", "--knowledge")["tasks"]
            if not isinstance(tasks, list):
                raise ValueError("no tasks list")
            lessons = [e for t in tasks if isinstance(t, dict) and isinstance(t.get("id"), int) and is_active(t)
                       if (e := entry(t))]
        except (OSError, ValueError, KeyError, TypeError, AttributeError, RuntimeError, subprocess.SubprocessError) as e:
            print(f"lessons-export: Dibs read failed, cache unchanged: {e}", file=sys.stderr)
            return 2
        write_cache(lessons)
        print(f"lessons-export: {len(lessons)} active lessons")
    return 0


if __name__ == "__main__":
    sys.exit(main())
