#!/usr/bin/env python3
"""Keep the feature atlas off the interactive path.

  atlas-refresh.py sync-hints            write each atlas parent's `## Pending since last refresh` section
                                         from the hint queue (DIBS_ATLAS_HINTS, filled by the dibs block)
  atlas-refresh.py queue --repo PATH     a merge landed in PATH (git post-merge hook): queue it and, unless
                                         the selected Claude session or weekly quota exceeds ATLAS_QUOTA_MAX (70), start `run`
  atlas-refresh.py run [--nightly]       refresh the stale subsystems of every queued repo in a headless
                                         Sonnet session each, that session stopped as soon as its turn ends;
                                         --nightly uses a 90% threshold instead of 70%
  atlas-refresh.py install-hooks         add the post-merge hook to every atlas repo that has none

Interactive sessions only write hint lines; they never refresh a stale atlas. Exit 0 always for queue
(it runs inside a git hook).
"""
import argparse
import contextlib
import datetime
import fcntl
import importlib.machinery
import importlib.util
import json
import math
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
try:
    QUOTA_MAX = min(99, max(0, int(os.environ.get("ATLAS_QUOTA_MAX", "70"))))
except ValueError:
    QUOTA_MAX = -1  # Keep queueing but never launch on invalid configuration.
HARD_MAX = 90
CLAUDE_PROFILE = os.environ.get("ATLAS_CLAUDE_PROFILE", "personal")
QUOTA_MAX_AGE = 3600
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


@contextlib.contextmanager
def queue_lock(suffix=""):
    path = QUEUE + suffix + ".lock"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


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
        if p.returncode != 0:
            return 100
        profile = json.loads(p.stdout)["agents"]["claude"]["profiles"][CLAUDE_PROFILE]
        if not profile.get("ok"):
            return 100
        quota = profile["quota"]
        captured = datetime.datetime.fromisoformat(quota["captured_at"].replace("Z", "+00:00"))
        if captured.tzinfo is None or not 0 <= time.time() - captured.timestamp() <= QUOTA_MAX_AGE:
            return 100
        values = [quota[key]["pct"] for key in ("session", "week_all")]
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or
               not math.isfinite(value) or not 0 <= value <= 100 for value in values):
            return 100
        return max(values)
    except (OSError, ValueError, KeyError, TypeError, OverflowError, subprocess.TimeoutExpired):
        return 100  # Unknown or stale quota must defer rather than launch.


def own_commits_only(repo):
    """True when every commit the merge brought in (ORIG_HEAD..HEAD) is by this repo's configured user.

    The refresh runs an unattended auto-mode session over the repo, so code that arrived from someone
    else's pull or merge is never allowed to start one.
    """
    def git(*a):
        return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True)
    me = git("config", "user.email").stdout.strip()
    log = git("log", "--format=%ae", "ORIG_HEAD..HEAD")
    return bool(me) and log.returncode == 0 and set(log.stdout.split()) <= {me}


def queue(repo):
    repo = os.path.realpath(repo)
    if not own_commits_only(repo):
        print(f"atlas-refresh: {repo}: merge brought in commits by others (or no ORIG_HEAD), not queued", file=sys.stderr)
        return
    head = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    with queue_lock():
        append_jsonl(QUEUE, {"ts": int(time.time()), "repo": repo, "head": head})
    if quota_pct() <= min(QUOTA_MAX, 99):
        subprocess.Popen([sys.executable, os.path.abspath(__file__), "run"], start_new_session=True,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def stale_subsystems(repo):
    p = subprocess.run([os.path.join(HERE, "..", "hooks", "atlas-helper.py"), "stale", repo], capture_output=True,
                       text=True, env={**os.environ, "ATLAS_CACHE_TTL": "0"}, timeout=60)
    if p.returncode != 0:
        raise RuntimeError(f"atlas helper failed: {p.stderr.strip()}")
    result = json.loads(p.stdout)
    if (not isinstance(result, dict) or not result.get("atlas") or
            not isinstance(result.get("subsystems"), list) or not result["subsystems"] or
            not isinstance(result.get("stale"), list)):
        raise RuntimeError("atlas helper returned an incomplete result")
    subsystems = {}
    for sub in result["subsystems"]:
        if (not isinstance(sub, dict) or not isinstance(sub.get("id"), str) or not sub["id"] or
                sub["id"] in subsystems or not isinstance(sub.get("owned"), list) or not sub["owned"] or
                not all(isinstance(path, str) and path for path in sub["owned"])):
            raise RuntimeError("atlas helper returned invalid subsystem inventory")
        subsystems[sub["id"]] = sub["owned"]
    stale = result["stale"]
    if not all(isinstance(s, dict) and s.get("id") in subsystems for s in stale):
        raise RuntimeError("atlas helper returned invalid stale subsystems")
    return result["atlas"], subsystems, [s["id"] for s in stale]


def stop_session(repo, session):
    """Stops the session this run created; a timeout leaves it working, which needs --force."""
    for extra in ([], ["--force"]):
        k = subprocess.run(["sessioneer", "--kill", session, *extra], capture_output=True, text=True)
        if k.returncode == 0:
            return True
    print(f"atlas-refresh: {repo}: could not stop {session}: {(k.stderr or k.stdout).strip()}", file=sys.stderr)
    return False


def refresh(repo, subsystem):
    """Runs one refresh turn and stops the session it started, whether the turn worked or not.

    sessioneer --wait documents that whoever starts the turn must --kill it: the turn
    ends idle and the session keeps a slot and a dashboard row until then. The --json
    envelope carries the session name even on a timeout, so the kill always names the
    exact session this call created. Netting that out leaves an unattended refresh with
    nothing of its own to clean up later.
    """
    prompt = (f"Headless atlas refresh. Run /feature-atlas-subsystem {subsystem} for this repo's atlas: refresh that one "
              "subsystem in place, stamp it at HEAD, patch the parent. Edit no source file and nothing else.")
    p = subprocess.run(["sessioneer", "--wait", "--json", "--timeout", "1800", "--workdir", repo, "--model", "sonnet",
                        "--effort", "medium", "--mode", "auto", "--profile", CLAUDE_PROFILE, prompt], capture_output=True, text=True)
    try:
        session = (json.loads(p.stdout or "{}") or {}).get("session")
    except ValueError:
        session = None
    if session:
        stop_session(repo, session)
    return p.returncode == 0


def run(nightly):
    with queue_lock(".run"):
        run_locked(nightly)


def run_locked(nightly):
    with queue_lock():
        queued = read_jsonl(QUEUE)
    left = []
    for repo in dict.fromkeys(q["repo"] for q in queued):
        limit = HARD_MAX if nightly else min(QUOTA_MAX, 99)
        if quota_pct() > limit:
            left.append({"repo": repo})
            continue
        try:
            atlas, before, stale = stale_subsystems(repo)
            done = []
            for subsystem in stale:
                if quota_pct() > limit:
                    break
                cutoff = int(time.time()) - 1
                if not refresh(repo, subsystem):
                    continue
                verified_atlas, subsystems, remaining = stale_subsystems(repo)
                if (verified_atlas == atlas and subsystem in subsystems and subsystem not in remaining
                        and set(before[subsystem]).issubset(subsystems[subsystem])):
                    done.append((subsystem, cutoff))
        except (RuntimeError, ValueError, OSError, subprocess.TimeoutExpired) as e:
            left.append({"repo": repo})
            print(f"atlas-refresh: {repo}: verification failed: {e}", file=sys.stderr)
            continue
        if done:
            for subsystem, cutoff in done:
                append_jsonl(HINTS, {"ts": cutoff, "repo": repo, "refreshed": [subsystem]})
            print(f"{repo}: refreshed {', '.join(s for s, _ in done)}")
        if len(done) < len(stale):
            left.append({"repo": repo})
            print(f"atlas-refresh: {repo}: {len(stale) - len(done)} of {len(stale)} refreshes did not finish, queued again",
                  file=sys.stderr)
    with queue_lock():
        current = read_jsonl(QUEUE)
        # Only consume the snapshot; queue() may have appended more while a refresh ran.
        remaining = current[len(queued):] if current[:len(queued)] == queued else current
        remaining.extend({"ts": int(time.time()), "repo": q["repo"], "head": q.get("head", "")} for q in left)
        if remaining:
            temp = QUEUE + f".{os.getpid()}.tmp"
            with open(temp, "w") as f:
                for rec in remaining:
                    f.write(json.dumps(rec) + "\n")
            os.replace(temp, QUEUE)
        elif os.path.exists(QUEUE):
            os.remove(QUEUE)
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
