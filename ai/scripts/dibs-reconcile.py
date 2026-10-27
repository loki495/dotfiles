#!/usr/bin/env python3
"""Mechanical Dibs invariant check (no model session). Never pushes, never leaves the host.

Also refreshes the rule export (ai/rules.md and the private file; committed, never pushed).
Checks: atlas Verified at vs branch tip, dead-owner claims, plans whose Status misses a closed
step, closed plan steps without a commit. Temporary records are excluded. Findings go into ONE standing issue (body rewritten
only when it changed); an atlas violation also gets one task under it, keyed by an idempotency
key, and that task is closed once the violation clears.

Usage: dibs-reconcile.py [--dry-run] [--behind-task N]     (see ai/scripts/README.md)
Exit: 0 ok, 2 Dibs unreachable (nothing written).
"""
import argparse
import importlib.machinery
import importlib.util
import os
import re
import sys

_here = os.path.dirname(os.path.abspath(__file__))
_loader = importlib.machinery.SourceFileLoader("dibs_measure", os.path.join(_here, "dibs-measure.py"))
M = importlib.util.module_from_spec(importlib.util.spec_from_loader("dibs_measure", _loader))
_loader.exec_module(M)
_xl = importlib.machinery.SourceFileLoader("rules_export", os.path.join(_here, "rules-export.py"))
RULES_EXPORT = importlib.util.module_from_spec(importlib.util.spec_from_loader("rules_export", _xl))
_xl.exec_module(RULES_EXPORT)

STANDING_TITLE = "Reconciler findings"
LABEL = "reconciler"
AREA = int(os.environ.get("RECONCILER_AREA", "2"))  # Personal Projects
GROUP = os.environ.get("RECONCILER_GROUP", "AI workflows")
BEHIND_TASK = int(os.environ.get("RECONCILER_BEHIND_TASK", "3"))  # commits behind before a task is filed
# Steps closed before the completion guards landed carry no structured evidence; not violations.
SINCE = os.environ.get("RECONCILER_SINCE", "2026-10-24")
MAX_TASKS = int(os.environ.get("RECONCILER_MAX_TASKS", "10"))  # open violation tasks; the rest only appear in the standing issue
KEY_RE = re.compile(r"^Key: (\S+)", re.M)


def atlas_findings(atlases, behind_task):
    """[(key, line, needs_task)] for atlases with an unverifiable stamp or too far behind."""
    out = []
    for x in atlases:
        r = M.atlas_drift(x.get("title", "?"), x.get("body", ""))
        name = r["atlas"]
        if r["problem"]:
            out.append((f"reconciler:atlas:{name}:{r['stamp']}", f"atlas {name}: {r['status']}", True))
        elif r["max_behind"] > 0:
            out.append((f"reconciler:atlas:{name}:{r['stamp']}",
                        f"atlas {name}: {r['max_behind']} commits behind ({r['files']} files)",
                        r["max_behind"] >= behind_task))
    return out


def plan_findings(plans):
    """plans: [show-json]. Closed steps missing from the plan body, closed steps with no commit."""
    out = []
    for p, steps_closing in plans:
        if p.get("temporary"):
            continue
        for c in p.get("children", []):
            if c.get("temporary"):
                continue
            closing = steps_closing.get(c["id"]) or {}
            if c.get("state") != "CLOSED" or str(closing.get("closedAt", ""))[:10] < SINCE:
                continue
            tag = re.match(r"S\d+[a-z]?\b", c["title"])
            mention = tag.group(0) if tag else f"#{c['id']}"
            if not re.search(rf"\b{re.escape(mention)}\b", p.get("body") or ""):
                out.append(f"plan {p['id']}: closed step {c['id']} ({mention}) not in the plan body")
            res = closing.get("result") or {}
            if not re.match(r"[0-9a-f]{7,40}\b", str(res.get("commit", ""))):
                out.append(f"step {c['id']} ({c['title'][:40]}): closed without a commit SHA")
    return out


def gather():
    """Read Dibs; raises RuntimeError/ValueError if unreachable."""
    tasks = [t for t in M.dibs_json("todo:agent:list")["tasks"] if not t.get("temporary")]
    listed = [t for t in M.dibs_json("todo:agent:list", "--knowledge")["tasks"] if not t.get("temporary")]
    atlases = [M.dibs_json("todo:agent:show", str(t["id"])) for t in listed
               if M.ATLAS_LABEL in t.get("labels", []) and t.get("state") == "OPEN"]
    plans = []
    for t in tasks:
        if "plan" in t.get("labels", []) and t.get("state") == "OPEN":
            p = M.dibs_json("todo:agent:show", str(t["id"]))
            closing = {c["id"]: M.dibs_json("todo:agent:show", str(c["id"])).get("closing")
                       for c in p.get("children", []) if c.get("state") == "CLOSED" and not c.get("temporary")}
            plans.append((p, closing))
    standing = next((t for t in tasks if t.get("title") == STANDING_TITLE and t.get("state") == "OPEN"), None)
    return tasks, atlases, plans, standing


def open_violation_tasks(standing):
    """{key: task id} of the open child tasks of the standing issue."""
    out = {}
    for c in M.dibs_json("todo:agent:show", str(standing["id"])).get("children", []):
        if c.get("state") == "OPEN":
            m = KEY_RE.search(M.dibs_json("todo:agent:show", str(c["id"])).get("body") or "")
            if m:
                out[m.group(1)] = c["id"]
    return out


def render(atlas, dead, plan, unfiled=0, cap=MAX_TASKS):
    def sec(title, lines):
        return f"## {title} ({len(lines)})\n" + ("\n".join(f"- {l}" for l in lines) or "none") + "\n"
    return ("Regenerated by ai/scripts/dibs-reconcile.py; edits are overwritten.\n\n"
            + sec("Atlas drift", [l for _, l, _ in atlas]
                  + ([f"{unfiled} more violations not filed as tasks (cap {cap})"] if unfiled else [])) + "\n"
            + sec("Dead-owner claims", dead) + "\n" + sec("Plans and closed steps", plan))


def reconcile(dry_run=False, behind_task=BEHIND_TASK, max_tasks=MAX_TASKS, out=print):
    tasks, atlases, plans, standing = gather()
    atlas = atlas_findings(atlases, behind_task)
    dead = [f"#{t['id']} {str(t.get('title', ''))[:60]} - {t['claim'].get('agentName')}"
            for t in M.dead_claims(tasks)]
    plan = plan_findings(plans)
    open_children = open_violation_tasks(standing) if standing else {}
    wanted = {k: l for k, l, need in atlas if need}
    # Existing tasks keep their slot; new ones only fill what is left under the cap.
    room = max(0, max_tasks - sum(k in wanted for k in open_children))
    new = [k for k in wanted if k not in open_children]
    for k in new[room:]:
        del wanted[k]
    body = render(atlas, dead, plan, len(new[room:]), max_tasks)
    out(body)
    if dry_run:
        out(f"dry-run: would keep tasks for {sorted(wanted) or 'no violations'}")
        return
    if standing is None:
        standing = M.dibs_json("todo:agent:create", STANDING_TITLE, "--body", body, "--area", str(AREA),
                               "--new-group", GROUP, "--new-label", LABEL,
                               "--idempotency-key", "reconciler:standing")
    else:
        cur = M.dibs_json("todo:agent:show", str(standing["id"]))
        if (cur.get("body") or "").strip() != body.strip():
            M.dibs_json("todo:agent:update", str(standing["id"]), "--body", body,
                        "--expected-revision", str(cur["revision"]))
    sid = standing["id"]
    for key, line in wanted.items():
        if key not in open_children:
            M.dibs_json("todo:agent:create", f"Reconciler: {line}"[:120], "--body",
                        f"Key: {key}\n{line}\nRefresh the atlas subsystems the commits touched and "
                        "restamp Verified at; this task closes itself once the stamp is current.",
                        "--parent", str(sid), "--area", str(AREA), "--new-group", GROUP,
                        "--new-label", LABEL, "--idempotency-key", key)
    for key, tid in open_children.items():
        if key not in wanted:
            claim = M.dibs_json("todo:agent:claim", str(tid), "--agent", "reconciler:script:none",
                                "--pid", str(os.getpid()), "--minutes", "5")
            M.dibs_json("todo:agent:complete", str(tid), "--pid", str(os.getpid()),
                        "--token", claim["capabilityToken"], "--reason", "COMPLETED",
                        "--summary", "Violation cleared (atlas stamp current or stamp changed).",
                        "--force", "--force-reason", "closed by the reconciler: the violation cleared")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="print findings, write nothing")
    ap.add_argument("--behind-task", type=int, default=BEHIND_TASK)
    ap.add_argument("--max-tasks", type=int, default=MAX_TASKS)
    a = ap.parse_args()
    try:
        reconcile(a.dry_run, a.behind_task, a.max_tasks)
        if not a.dry_run:
            for p in RULES_EXPORT.export(do_commit=True):
                print(f"rules export updated {p}")
    except (RuntimeError, ValueError, OSError, KeyError) as e:
        print(f"Dibs unreachable or unreadable, nothing written: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
