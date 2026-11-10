#!/usr/bin/env python3
"""Atlas lookups for the commit and push hooks.

  atlas-helper.py touched <repo> <file>...   subsystems whose owned paths contain any file
  atlas-helper.py stale   <repo>             subsystems changed since their Verified at (push gate)

Prints JSON. Prints {"skipped": reason} when Dibs cannot be read, {} when the repo has no atlas.
DIBS_CMD overrides the command prefix (tests); the atlas is cached per repo for ATLAS_CACHE_TTL
seconds (default 300) under $XDG_RUNTIME_DIR.
"""
import hashlib
import importlib.machinery
import importlib.util
import json
import os
import re
import shlex
import stat
import subprocess
import sys
import time

CMD = shlex.split(os.environ.get("DIBS_CMD", "docker exec -u www-data dibs-app php artisan"))
TTL = int(os.environ.get("ATLAS_CACHE_TTL", "300"))
CACHE_DIR = os.environ.get("XDG_RUNTIME_DIR") or os.path.expanduser("~/.cache/atlas-hook")
SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")
_here = os.path.dirname(os.path.realpath(__file__))
_l = importlib.machinery.SourceFileLoader("dm", os.path.join(_here, "..", "scripts", "dibs-measure.py"))
DM = importlib.util.module_from_spec(importlib.util.spec_from_loader("dm", _l))
_l.exec_module(DM)


def dibs(*args):
    p = subprocess.run([*CMD, *args], capture_output=True, text=True, timeout=15)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or "dibs failed")
    return json.loads(p.stdout)


def git(repo, *args):
    p = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    return p.returncode, p.stdout.strip()


def load_atlas(repo):
    os.makedirs(CACHE_DIR, mode=0o700, exist_ok=True)
    cache = os.path.join(CACHE_DIR, "atlas-" + hashlib.sha1(repo.encode()).hexdigest()[:12] + ".json")
    try:
        st = os.lstat(cache)
        # Only trust a regular file we own; anything else (symlink, other user's) is ignored.
        if stat.S_ISREG(st.st_mode) and st.st_uid == os.getuid() and time.time() - st.st_mtime < TTL:
            return clean(json.load(open(cache)))
    except (OSError, ValueError):
        pass
    out = {}
    for t in dibs("todo:agent:list", "--knowledge")["tasks"]:
        if DM.ATLAS_LABEL not in t.get("labels", []) or t.get("state") != "OPEN":
            continue
        d = dibs("todo:agent:show", str(t["id"]), "--all-comments")
        r, branch, sha = DM.parse_atlas(d.get("body", ""))
        if not r or os.path.realpath(r) != repo:
            continue
        comments = d.get("comments", {})
        if not isinstance(comments, dict) or comments.get("complete") is not True or comments.get("lastPage", 1) > 1:
            raise ValueError("atlas comments incomplete")
        subs = []
        for c in comments.get("items", []):
            if c.get("withheld"):
                raise ValueError("atlas comment withheld")
            b = c.get("body", "")
            m = re.search(r"^subsystem:[ \t]*(\S+)", b, re.M)
            v = re.search(r"^verified-at:[ \t]*([0-9a-f]{7,40})", b, re.M)
            o = re.search(r"^owned_paths:[ \t]*(.+)$", b, re.M)
            if re.search(r"^subsystem:", b, re.M) and not m:
                raise ValueError("malformed atlas subsystem header")
            if m and (not v or not o or not o.group(1).strip()):
                raise ValueError("malformed atlas subsystem")
            if m and v and o:
                owned = [x.strip() for x in o.group(1).split(",") if x.strip()]
                if not owned:
                    raise ValueError("malformed atlas subsystem ownership")
                subs.append({"id": m.group(1), "verified_at": v.group(1), "owned": owned})
        if not subs:
            raise ValueError("atlas has no verifiable subsystems")
        out = clean({"atlas": d["id"], "branch": branch, "stamp": sha, "subsystems": subs})
        break
    tmp = f"{cache}.{os.getpid()}"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as fh:
        json.dump(out, fh)
    os.replace(tmp, cache)
    return out


def clean(a):
    """Drop subsystems whose stamp is not a plain hex SHA, so a bad cache or atlas never reaches git."""
    if a:
        subs = a.get("subsystems", [])
        if any(not SHA_RE.fullmatch(str(s.get("verified_at", ""))) for s in subs):
            raise ValueError("invalid atlas subsystem stamp")
    return a


def owns(owned, f):
    return any(f == o or (o.endswith("/") and f.startswith(o)) or f.startswith(o.rstrip("/") + "/")
               for o in owned)


def main():
    cmd, repo = sys.argv[1], os.path.realpath(sys.argv[2])
    try:
        a = load_atlas(repo)
    except (RuntimeError, ValueError, OSError, subprocess.TimeoutExpired) as e:
        print(json.dumps({"skipped": str(e)[:200]}))
        return
    if not a:
        print("{}")
        return
    if cmd == "touched":
        files = sys.argv[3:]
        touched = []
        for sub in a["subsystems"]:
            result = subprocess.run(["git", "-C", repo, "ls-files", "--cached", "--others", "--full-name", "-z", "--", *sub["owned"]],
                                    capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError("git ls-files failed while matching atlas ownership")
            staged = subprocess.run(["git", "-C", repo, "diff", "--cached", "--no-renames", "--name-only", "-z", "HEAD", "--", *sub["owned"]],
                                    capture_output=True, text=True)
            if staged.returncode != 0:
                raise RuntimeError("git diff failed while matching atlas ownership")
            owned = set(result.stdout.split("\0")) | set(staged.stdout.split("\0"))
            if any(f in owned for f in files):
                touched.append(sub["id"])
        print(json.dumps({"atlas": a["atlas"], "subsystems": touched}))
    elif cmd == "stale":
        _, cur = git(repo, "symbolic-ref", "--short", "HEAD")
        if a["branch"] and a["branch"] != cur:
            print("{}")
            return
        stale = []
        for s in a["subsystems"]:
            if git(repo, "merge-base", "--is-ancestor", s["verified_at"], "HEAD")[0] != 0:
                stale.append({"id": s["id"], "why": f"stamp {s['verified_at']} is not on this branch"})
                continue
            code, diff = git(repo, "diff", "--name-only", s["verified_at"], "HEAD", "--", *s["owned"])
            if code != 0:
                raise RuntimeError("git diff failed while checking atlas coverage")
            hit = diff.splitlines()
            if hit:
                stale.append({"id": s["id"], "why": f"{len(hit)} owned file(s) changed since {s['verified_at']}"})
        print(json.dumps({"atlas": a["atlas"], "subsystems": [{"id": s["id"], "owned": s["owned"]} for s in a["subsystems"]], "stale": stale}))


main()
