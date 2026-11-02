#!/usr/bin/env python3
"""Keep the feature atlas off the interactive path.

  atlas-refresh.py sync-hints            write each atlas parent's `## Pending since last refresh` section
                                         from the hint queue (DIBS_ATLAS_HINTS, filled by the dibs block)
  atlas-refresh.py queue --repo PATH     a merge landed in PATH (git post-merge hook): queue it and, unless
                                         the Claude 5h quota is above ATLAS_QUOTA_MAX (default 70), start `run`
  atlas-refresh.py run [--nightly]       refresh the stale subsystems of every queued repo in a headless
                                         Sonnet session each; --nightly ignores the quota threshold (not 90)
  atlas-refresh.py install-hooks         add the post-merge hook to every atlas repo that has none

Interactive sessions only write hint lines; they never refresh a stale atlas. Exit 0 always for queue
(it runs inside a git hook).
"""
import argparse
import importlib.machinery
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
HINTS = os.environ.get("DIBS_ATLAS_HINTS") or os.path.expanduser("~/.local/state/dibs-atlas-hints.jsonl")
QUEUE = os.environ.get("ATLAS_QUEUE") or os.path.expanduser("~/.local/state/dibs-atlas-queue.jsonl")
SECTION = "## Pending since last refresh"
QUOTA_MAX = int(os.environ.get("ATLAS_QUOTA_MAX", "70"))
HARD_MAX = 90
MARK = "# atlas-refresh"
_l = importlib.machinery.SourceFileLoader("dm", os.path.join(HERE, "dibs-measure.py"))
DM = importlib.util.module_from_spec(importlib.util.spec_from_loader("dm", _l))
_l.exec_module(DM)


def read_jsonl(path):
    try:
        with open(path) as f:
            return [json.loads(x) for x in f if x.strip()]
    except OSError:
        return []


def append_jsonl(path, rec):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(rec) + "\n")


def pending(records, repo):
    """Hint records for repo not yet covered by a later refresh of the same subsystem, oldest first."""
    done = {}
    for r in records:
        if r.get("refreshed") and r.get("repo") == repo:
            for s in r["refreshed"]:
                done[s] = max(done.get(s, 0), r["ts"])
    return [r for r in records if "subsystem" in r and r.get("repo") == repo and r["ts"] > done.get(r["subsystem"], 0)]


def with_section(body, hints):
    """body with its Pending section replaced by one listing hints (removed when there are none)."""
    body = re.sub(rf"\n*{re.escape(SECTION)}\n.*?(?=\n## |\Z)", "", body or "", flags=re.S).rstrip()
    if not hints:
        return body + "\n"
    lines = [f"- {h['subsystem']}: {h['change']} ({h['head'][:9]}, {time.strftime('%Y-%m-%d', time.gmtime(h['ts']))})" for h in hints]
    return f"{body}\n\n{SECTION}\n" + "\n".join(lines) + "\n"


def atlas_parents():
    out = []
    for t in DM.dibs_json("todo:agent:list", "--knowledge")["tasks"]:
        if DM.ATLAS_LABEL in t.get("labels", []) and t.get("state") == "OPEN":
            d = DM.dibs_json("todo:agent:show", str(t["id"]))
            repo = DM.parse_atlas(d.get("body", ""))[0]
            if repo:
                out.append((os.path.realpath(repo), d))
    return out


def sync_hints():
    records = read_jsonl(HINTS)
    for repo, d in atlas_parents():
        new = with_section(d.get("body", ""), pending(records, repo))
        if new.strip() != (d.get("body") or "").strip():
            DM.dibs_json("todo:agent:update", str(d["id"]), f"--expected-revision={d['revision']}", f"--body={new}")
            print(f"{d['title']}: pending section updated")


def quota_pct():
    try:
        p = subprocess.run(["sessioneer", "--usage"], capture_output=True, text=True, timeout=60)
        return int(json.loads(p.stdout)["agents"]["claude"]["quota"]["session"]["pct"])
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired):
        return 100  # unknown quota: defer to the nightly batch


def own_commits_only(repo):
    """True when every commit the merge brought in (ORIG_HEAD..HEAD) is by this repo's configured user.

    The refresh runs an unattended auto-mode session over the repo, so code that arrived from someone
    else's pull or merge is never allowed to start one.
    """
    def git(*a):
        return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True)
    me = git("config", "user.email").stdout.strip()
    log = git("log", "--no-merges", "--format=%ae", "ORIG_HEAD..HEAD")
    return bool(me) and log.returncode == 0 and set(log.stdout.split()) <= {me}


def queue(repo):
    repo = os.path.realpath(repo)
    if not own_commits_only(repo):
        print(f"atlas-refresh: {repo}: merge brought in commits by others (or no ORIG_HEAD), not queued", file=sys.stderr)
        return
    head = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    append_jsonl(QUEUE, {"ts": int(time.time()), "repo": repo, "head": head})
    if quota_pct() <= QUOTA_MAX:
        subprocess.Popen([sys.executable, os.path.abspath(__file__), "run"], start_new_session=True,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def stale_subsystems(repo):
    p = subprocess.run([os.path.join(HERE, "..", "hooks", "atlas-helper.py"), "stale", repo], capture_output=True,
                       text=True, env={**os.environ, "ATLAS_CACHE_TTL": "0"}, timeout=60)
    return [s["id"] for s in json.loads(p.stdout or "{}").get("stale", [])]


def refresh(repo, subsystem):
    prompt = (f"Headless atlas refresh. Run /feature-atlas-subsystem {subsystem} for this repo's atlas: refresh that one "
              "subsystem in place, stamp it at HEAD, patch the parent. Edit no source file and nothing else.")
    return subprocess.run(["sessioneer", "--wait", "--timeout", "1800", "--workdir", repo, "--model", "sonnet",
                           "--effort", "medium", "--mode", "auto", prompt]).returncode == 0


def run(nightly):
    queued = read_jsonl(QUEUE)
    left = []
    for repo in dict.fromkeys(q["repo"] for q in queued):
        limit = HARD_MAX if nightly else QUOTA_MAX
        if quota_pct() > limit:
            left.append({"repo": repo})
            continue
        done = [s for s in stale_subsystems(repo) if refresh(repo, s)]
        if done:
            append_jsonl(HINTS, {"ts": int(time.time()) + 1, "repo": repo, "refreshed": done})
            print(f"{repo}: refreshed {', '.join(done)}")
    if os.path.exists(QUEUE):
        os.remove(QUEUE)
    for q in left:
        append_jsonl(QUEUE, {"ts": int(time.time()), "repo": q["repo"], "head": ""})
    sync_hints()


def install_hooks():
    body = ('#!/bin/sh\n' + MARK + '\n'
            'python3 "$HOME/dotfiles/ai/scripts/atlas-refresh.py" queue --repo "$(git rev-parse --show-toplevel)" >/dev/null 2>&1 &\n')
    for repo, _ in atlas_parents():
        hooks = subprocess.run(["git", "-C", repo, "rev-parse", "--git-path", "hooks"], capture_output=True, text=True).stdout.strip()
        if not hooks:
            continue
        path = os.path.join(repo, hooks) if not os.path.isabs(hooks) else hooks
        path = os.path.join(path, "post-merge")
        if os.path.exists(path) and MARK not in Path(path).read_text():
            print(f"{repo}: has its own post-merge hook, left alone")
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w").write(body)
        os.chmod(path, 0o755)
        print(f"{repo}: post-merge hook installed")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sync-hints")
    sub.add_parser("install-hooks")
    sub.add_parser("queue").add_argument("--repo", required=True)
    sub.add_parser("run").add_argument("--nightly", action="store_true")
    a = ap.parse_args()
    try:
        if a.cmd == "sync-hints":
            sync_hints()
        elif a.cmd == "install-hooks":
            install_hooks()
        elif a.cmd == "queue":
            queue(a.repo)
        else:
            run(a.nightly)
    except (RuntimeError, ValueError, OSError, subprocess.TimeoutExpired) as e:
        print(f"atlas-refresh: {e}", file=sys.stderr)
        return 0 if a.cmd == "queue" else 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
