#!/usr/bin/env python3
"""Repeatable workflow measurements for the Dibs plan (report only, always exits 0).

  1. atlas drift      each `feature atlas` parent vs its repo's branch tip
  2. push vs atlas    Claude sessions that ran `git push` vs edited an atlas afterwards
  3. dead claims      open Dibs tasks whose claim is no longer alive

Usage: dibs-measure.py [--days 30] [--until ISO] [--projects-dir DIR]
                       [--atlas-json FILE] [--claims-json FILE] [--skip-dibs]
See ai/scripts/README.md.
"""
import argparse
import collections
import datetime
import glob
import json
import os
import re
import subprocess
import sys
import time

DIBS_DIR = os.environ.get("DIBS_DIR", os.path.expanduser("~/www/personal/dibs"))
PROJECTS_DIR = os.path.expanduser("~/.claude/projects")
# Only dirs of these projects are scanned: -home-andres-www-personal-<name>
PROJECT_PREFIX = "-home-andres-www-personal-"
ATLAS_LABEL = "feature atlas"


def git(repo, *args):
    p = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    return p.returncode, p.stdout.strip()


def dibs_json(*args):
    cmd = ["docker", "compose", "exec", "-T", "-u", "www-data", "app",
           "php", "artisan", *args]
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=DIBS_DIR)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or "dibs CLI failed")
    return json.loads(p.stdout)


def parse_atlas(body):
    """(repo, branch, sha) from an atlas parent body; any may be None."""
    def field(name):
        m = re.search(rf"^{name}:\s*(.+)$", body or "", re.M)
        return m.group(1).strip() if m else None
    repo = field("Repo")
    if repo:
        m = re.match(r"(\S+)", repo)
        repo = os.path.expanduser(m.group(1).rstrip(",;"))
    branch = field("Branch")
    if branch:
        branch = re.match(r"[^\s(,;]+", branch).group(0)
    ver = field("Verified at")
    m = re.match(r"([0-9a-f]{7,40})\b", ver or "")
    return repo, branch, m.group(1) if m else None


def atlas_drift(title, body):
    repo, branch, sha = parse_atlas(body)
    row = {"atlas": re.sub(r"^Feature atlas:\s*", "", title), "stamp": (sha or "-")[:9],
           "status": "", "behind": "-", "files": "-"}
    if not repo or not sha or not os.path.isdir(repo):
        row["status"] = "no repo/stamp"
        return row
    if not branch:
        _, branch = git(repo, "symbolic-ref", "--short", "HEAD")
        branch = branch or "HEAD"
    tips = [(ref, git(repo, "rev-parse", "--verify", "-q", ref + "^{commit}"))
            for ref in (branch, "origin/" + branch)]
    tips = [(r, o[1]) for r, o in tips if o[0] == 0]
    if not tips:
        row["status"] = f"branch {branch} missing"
        return row
    if git(repo, "cat-file", "-e", sha + "^{commit}")[0] != 0:
        row["status"] = "stamp unknown to repo"
        return row
    parts = []
    for ref, tip in tips:
        if git(repo, "merge-base", "--is-ancestor", sha, tip)[0] != 0:
            parts.append(f"{ref}: stamp NOT on branch")
            continue
        behind = git(repo, "rev-list", "--count", f"{sha}..{tip}")[1]
        files = len(git(repo, "diff", "--name-only", sha, tip)[1].splitlines())
        parts.append(f"{ref}: {behind} behind, {files} files")
        if ref == branch:
            row["behind"], row["files"] = behind, files
    row["status"] = "; ".join(parts)
    return row


def scan_push_atlas(projects_dir, days, until):
    """{project: [push_sessions, atlas_after_push, atlas_anywhere]}"""
    cut = until - days * 86400
    res = collections.defaultdict(lambda: [0, 0, 0])
    for proj in glob.glob(os.path.join(projects_dir, PROJECT_PREFIX + "*")):
        name = os.path.basename(proj)[len(PROJECT_PREFIX):]
        for f in glob.glob(proj + "/*.jsonl"):
            if not cut <= os.path.getmtime(f):
                continue
            push = atlas_after = atlas_any = False
            with open(f, errors="replace") as fh:
                for line in fh:
                    if '"tool_use"' not in line:
                        continue
                    try:
                        d = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if _ts(d) > until:
                        continue
                    content = (d.get("message") or {}).get("content")
                    if not isinstance(content, list):
                        continue
                    for b in content:
                        if not isinstance(b, dict) or b.get("type") != "tool_use":
                            continue
                        inp = b.get("input") or {}
                        n = b.get("name", "")
                        if n == "Bash" and "git push" in str(inp.get("command", "")):
                            push = True
                        elif n.startswith("mcp__dibs__") and n.endswith(("todo_comment", "todo_revise")) \
                                and "Verified at" in json.dumps(inp):
                            atlas_any = True
                            atlas_after = atlas_after or push
            if push:
                r = res[name]
                r[0] += 1
                r[1] += atlas_after
                r[2] += atlas_any
    return res


def _ts(d):
    t = d.get("timestamp")
    if not isinstance(t, str):
        return 0
    try:
        return datetime.datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0


def dead_claims(tasks):
    return [t for t in tasks
            if t.get("state") == "OPEN" and t.get("claim") and not t["claim"].get("isCurrentlyAlive")]


def table(rows, cols):
    w = [max(len(str(r[c])) for r in rows + [dict(zip(cols, cols))]) for c in cols]
    for r in [dict(zip(cols, cols))] + rows:
        print("  " + "  ".join(str(r[c]).ljust(x) for c, x in zip(cols, w)).rstrip())


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--until", help="ISO time; ignore activity after it (default now)")
    ap.add_argument("--projects-dir", default=PROJECTS_DIR)
    ap.add_argument("--atlas-json", help="[{title, body}] instead of reading Dibs")
    ap.add_argument("--claims-json", help="[{state, claim}] instead of reading Dibs")
    ap.add_argument("--skip-dibs", action="store_true")
    a = ap.parse_args()
    until = datetime.datetime.fromisoformat(a.until).timestamp() if a.until else time.time()

    print("== 1. Atlas drift")
    atlases, tasks = [], []
    try:
        if a.atlas_json:
            atlases = json.load(open(a.atlas_json))
        elif not a.skip_dibs:
            listed = dibs_json("todo:agent:list", "--knowledge")["tasks"]
            atlases = [dibs_json("todo:agent:show", str(t["id"])) for t in listed
                       if ATLAS_LABEL in t.get("labels", []) and t.get("state") == "OPEN"]
        if a.claims_json:
            tasks = json.load(open(a.claims_json))
        elif not a.skip_dibs:
            tasks = dibs_json("todo:agent:list")["tasks"]
    except (RuntimeError, OSError, ValueError, KeyError) as e:
        print(f"  Dibs unreadable: {e}", file=sys.stderr)
    rows = [atlas_drift(x.get("title", "?"), x.get("body", "")) for x in atlases]
    if rows:
        table(rows, ["atlas", "stamp", "status"])
    stale = [r for r in rows if r["behind"] not in ("-", "0")]
    print(f"summary: {len(rows)} atlases, {len(stale)} behind their branch tip, "
          f"{sum('NOT on branch' in r['status'] or 'unknown' in r['status'] for r in rows)} with an unverifiable stamp")

    print("\n== 2. Push vs atlas (sessions in window)")
    res = scan_push_atlas(a.projects_dir, a.days, until)
    rows = [{"project": k, "push": v[0], "atlas_after_push": v[1], "atlas_any": v[2]}
            for k, v in sorted(res.items())]
    if rows:
        table(rows, ["project", "push", "atlas_after_push", "atlas_any"])
    print("summary: " + (", ".join(f"{r['project']} {r['atlas_after_push']}/{r['push']}" for r in rows)
                         or "no push sessions") + "  (atlas edited after first push / sessions with push)")

    print("\n== 3. Claims and closing notes")
    dead = dead_claims(tasks)
    for t in dead:
        print(f"  #{t.get('id')} {str(t.get('title', ''))[:60]} - {t['claim'].get('agentName')}")
    print(f"summary: {len(dead)} open tasks hold a dead claim of {len(tasks)} open tasks; "
          "closed tasks without a commit SHA: n/a (the Dibs CLI does not list closed tasks)")


if __name__ == "__main__":
    main()
