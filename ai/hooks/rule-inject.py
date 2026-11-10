#!/usr/bin/env python3
"""Just-in-time rules: inject the few Dibs rule records an event is about, once per context lifetime.

One script for PreToolUse, PostToolUse, SessionStart and UserPromptSubmit. An event is turned into
trigger keys (git-commit, test-run, ...); the key -> rule ids maps come from the generated
ai/rules-triggers.json and ~/.dotfiles-private/ai/rules-triggers.private.json (RULE_TRIGGERS overrides,
':'-separated, merged by key). The private keys home-net and work-creds use regexes from
~/.dotfiles-private/ai/rule-keys.private.json (RULE_PRIVATE_KEYS). Rule texts come from the exports
ai/rules.md and ~/.dotfiles-private/ai/rules.private.md (RULE_FILES overrides), never from a live Dibs
call. A rule is sent only if its id@revision is absent from the delivered set $RULE_STATE_DIR (default
$XDG_RUNTIME_DIR/dibs-rules, else ~/.cache/dibs-rules)/<session>-<agent_id|main>. Everything is plain
additionalContext. Two checks ride along: a hyphenated Dibs label name gets a warning, and a prompt
gets a quota warning once usage (`$SESSIONEER_BIN --usage`, cached 300 s) reaches 90%.
Any failure is silent (exit 0): this hook never blocks on its own trouble.
"""
import contextlib
import fcntl
import glob
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.realpath(__file__))
DEFAULT_FILES = [os.path.join(os.path.dirname(HERE), "rules.md"),
                 os.path.expanduser("~/.dotfiles-private/ai/rules.private.md")]
DEFAULT_TRIGGERS = [os.path.join(os.path.dirname(HERE), "rules-triggers.json"),
                    os.path.expanduser("~/.dotfiles-private/ai/rules-triggers.private.json")]
DEFAULT_PRIVATE_KEYS = "~/.dotfiles-private/ai/rule-keys.private.json"
CAP = 9000  # additionalContext is capped at 10,000 characters
HEADING = re.compile(r"^## (\d+)@(\d+) (.*)$")

GIT = r"(^|[^\w-])git(\s+-\S+(\s+[^-\s]\S*)?)*\s+(%s)(\s|$)"
ARGS = r"([^\s&;|]+\s+)*"
BASH = [  # (key, regex on the command)
    ("git-commit", GIT % "commit"),
    ("git-push", GIT % "push"),
    ("git-history", GIT % "merge|rebase|worktree|cherry-pick|stash|reset"),
    ("git-history", GIT % "commit" + r".*--amend"),
    ("git-add-all", GIT % "add" + ARGS + r"(-A|--all|\.)(\s|$)"),
    ("git-add-all", GIT % "commit" + ARGS + r"(-[a-zA-Z]*a[a-zA-Z]*|--all)(\s|$)"),
    ("git-add-all", GIT % "checkout" + r"(--\s+)?\.(\s|$)"),
    ("git-add-all", GIT % "clean"),
    ("test-run", r"\b(pest|phpunit|pytest|vitest|jest)\b|\bartisan\s+test\b|\bnpm\s+(run\s+)?test\b"),
    ("php-tool", r"\b(artisan|composer|pint|phpstan|rector)\b"),
    ("live-check", r"\bcurl\b|\bdocker[ -]compose\s+(up|restart)\b"),
    ("db-cli", r"\b(mysql|mariadb|sqlite3|tinker|migrate)\b"),
    ("quota-check", r"\bsessioneer\s+--usage\b"),
    ("session-launch", r"\bsessioneer\b.*--(agent|model|effort|resume)\b"),
    ("peer-send", r"\bsessioneer\b.*--(send|peers)\b"),
    ("schedule", r"(^|[;&|])\s*(at|atq)(\s|$)|\bsleep\s+[1-9]\d{2,}"),
]
REMINDER = ("Rule 1226: end your reply with one status line: Safe to archive this session. / Continue in this "
            "session: ... / Continue in a different session: ... / Waiting on Andres: ... / Waiting on other "
            "work: ... / All planned work is done.")
TEST_FILE = re.compile(r"(^|/)tests?/|(^|/)test_|_test\.|\.test\.|\.spec\.|Test\.php$")
TOOLS = {  # tool name -> trigger key
    "Agent": "agent-launch", "Task": "agent-launch",
    "mcp__dibs__todo_create": "dibs-create", "mcp__dibs__todo_revise": "dibs-revise",
    "mcp__dibs__todo_comment": "dibs-comment", "mcp__dibs__todo_heartbeat": "dibs-comment",
    "mcp__dibs__todo_claim": "dibs-claim", "mcp__dibs__todo_complete": "dibs-complete",
    "mcp__dibs__todo_release": "dibs-release",
    "mcp__playwright__browser_take_screenshot": "screenshot",
}
LABEL_TOOLS = {"mcp__dibs__todo_create": ("labelNames", "newLabelName"), "mcp__dibs__todo_revise": ("addLabels",)}
QUOTA_LIMIT, QUOTA_TTL = 90, 300


TYPE_KEYS = {"code": ["live-repo"], "tests": ["test-file", "test-run"],
             "docs": ["md-edit", "project-doc"], "git": ["git-commit", "git-history", "git-add-all", "git-push"],
             "db": ["db-cli"], "live-site": ["live-check", "live-repo"],
             "dibs": ["dibs-create", "dibs-revise", "dibs-comment", "dibs-claim", "dibs-complete", "dibs-release"],
             "infra": ["home-net", "schedule", "live-check"], "research": []}
LATE = "This rule arrived after the call ran. Check that call and your earlier work in this session against it, and fix what it missed."


@contextlib.contextmanager
def state_lock(path):
    with open(path + ".lock", "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        yield


def rules_for_types(types, session_id, agent_id, tool_use_id=None):
    path = state_file({"session_id": session_id, "agent_id": agent_id})
    with state_lock(path):
        have, rules, triggers = delivered(path), load_rules(), load_triggers()
        same_call = set()
        if tool_use_id:
            try:
                with open(path + ".calls") as f:
                    for line in f:
                        call, revision = json.loads(line)
                        if call == tool_use_id:
                            same_call.add(revision)
            except (OSError, ValueError):
                pass
        ids = list(dict.fromkeys(i for kind in types for key in TYPE_KEYS.get(kind, []) for i in triggers.get(key, [])))
        fresh = [i for i in ids if i in rules and (f"{i}@{rules[i]['rev']}" not in have or
                                                        f"{i}@{rules[i]['rev']}" in same_call)]
        if fresh:
            with open(path, "a") as f:
                f.writelines(f"{i}@{rules[i]['rev']}\n" for i in fresh if f"{i}@{rules[i]['rev']}" not in have)
        return [f"[rule {i}] {rules[i]['text']}" for i in fresh]


def load_triggers():
    merged = {}
    files = os.environ.get("RULE_TRIGGERS")
    for path in files.split(":") if files else DEFAULT_TRIGGERS:
        try:
            data = json.load(open(path))
        except (OSError, ValueError):
            continue
        for key, ids in data.items() if isinstance(data, dict) else []:
            if isinstance(ids, list):
                merged.setdefault(key, []).extend(i for i in ids if isinstance(i, int))
    return merged


def private_key_patterns():
    try:
        data = json.load(open(os.path.expanduser(os.environ.get("RULE_PRIVATE_KEYS") or DEFAULT_PRIVATE_KEYS)))
    except (OSError, ValueError):
        return []
    out = []
    for key, rx in data.items() if isinstance(data, dict) else []:
        try:
            out.append((key, re.compile(rx)))
        except (re.error, TypeError):
            pass
    return out


def load_rules():
    rules = {}
    files = os.environ.get("RULE_FILES")
    for path in files.split(":") if files else DEFAULT_FILES:
        try:
            lines = open(path).read().splitlines()
        except OSError:
            continue
        cur = None
        for line in lines:
            m = HEADING.match(line)
            if m:
                cur = int(m.group(1))
                if cur in rules:  # first definition wins; a later file cannot override a rule
                    cur = None
                    continue
                rules[cur] = {"rev": int(m.group(2)), "text": []}
            elif cur is not None:
                rules[cur]["text"].append(line)
    return {k: {"rev": v["rev"], "text": "\n".join(v["text"]).strip()} for k, v in rules.items()}


def state_file(data):
    d = os.environ.get("RULE_STATE_DIR") or os.path.join(
        os.environ.get("XDG_RUNTIME_DIR") or os.path.expanduser("~/.cache"), "dibs-rules")
    os.makedirs(d, mode=0o700, exist_ok=True)
    clean = lambda s: re.sub(r"[^A-Za-z0-9_-]", "_", str(s))
    return os.path.join(d, f"{clean(data['session_id'])}-{clean(data.get('agent_id') or 'main')}")


def delivered(path):
    try:
        return set(open(path).read().split())
    except OSError:
        return set()


def git_root_has_compose(path):
    d = os.path.dirname(os.path.abspath(path))
    while d != os.path.dirname(d):
        if os.path.exists(os.path.join(d, ".git")):
            return any(os.path.exists(os.path.join(d, n)) for n in
                       ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"))
        d = os.path.dirname(d)
    return False


def match(data):
    """The trigger keys the event is about."""
    ev, tool, inp = data.get("hook_event_name"), data.get("tool_name", ""), data.get("tool_input") or {}
    if ev == "UserPromptSubmit":
        prompt = str(data.get("prompt", ""))
        keys = [k for k, rx in private_key_patterns() if rx.search(prompt)]
        if prompt.startswith("[sessioneer peer:"):
            keys.append("peer-prompt")
        if re.match(r"(?i)(todo|next):", prompt):
            keys.append("todo-note")
        return keys
    if ev != "PreToolUse":
        return []
    if tool in TOOLS:
        return [TOOLS[tool]]
    if tool == "Bash":
        cmd = str(inp.get("command", ""))
        keys = [k for k, rx in BASH if re.search(rx, cmd)]
        return list(dict.fromkeys(keys + [k for k, rx in private_key_patterns() if rx.search(cmd)]))
    path = str(inp.get("file_path") or inp.get("notebook_path") or "")
    if tool in ("Edit", "Write", "MultiEdit", "NotebookEdit") and path:
        keys = []
        if path.startswith(os.path.expanduser("~/www/")) and git_root_has_compose(path):
            keys.append("live-repo")
        if TEST_FILE.search(path):
            keys.append("test-file")
        if path.endswith(".md"):
            keys.append("md-edit")
        if os.path.basename(path) in ("CLAUDE.md", "AGENTS.md"):
            keys.append("project-doc")
        return keys
    return []


def hyphen_labels(data):
    names = (data.get("tool_input") or {}).copy()
    labels = []
    for field in LABEL_TOOLS.get(data.get("tool_name"), ()):
        v = names.get(field)
        labels += v if isinstance(v, list) else [v]
    return [l for l in labels if isinstance(l, str) and "-" in l]


def read_quota(profile):
    try:
        r = subprocess.run([os.environ.get("SESSIONEER_BIN") or "sessioneer", "--usage"],
                           capture_output=True, text=True, timeout=10)
        if r.returncode:
            return None
        p = json.loads(r.stdout)["agents"]["claude"]["profiles"][profile]
        vals = [p["quota"]["session"]["pct"], p["quota"]["week_all"]["pct"]]
        ok = p.get("ok") and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in vals)
        return max(vals) if ok else None
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        return None


def profile_name():
    """This session's Claude profile: RULE_QUOTA_PROFILE, else from CLAUDE_CONFIG_DIR (.claude-work is work, .claude is personal)."""
    if os.environ.get("RULE_QUOTA_PROFILE"):
        return os.environ["RULE_QUOTA_PROFILE"]
    base = os.path.basename(os.environ.get("CLAUDE_CONFIG_DIR", "").rstrip("/"))
    m = re.fullmatch(r"\.claude-(.+)", base)
    return m.group(1) if m else "personal"


def quota_pct(state_dir, profile):
    """Highest quota percentage, or None; the reading is cached so prompts do not each run the binary."""
    cache = os.path.join(state_dir, "quota-" + re.sub(r"[^A-Za-z0-9_-]", "_", profile))
    try:
        stamp, pct = json.load(open(cache))
        if time.time() - stamp < QUOTA_TTL:
            return pct
    except (OSError, ValueError, TypeError):
        pass
    pct = read_quota(profile)
    with open(cache, "w") as f:
        json.dump([time.time(), pct], f)
    return pct


def work_order(obj):
    """The workOrder dict inside a todo_claim tool_response of any wrapping (dict, JSON string, content blocks)."""
    if isinstance(obj, str):
        try:
            return work_order(json.loads(obj))
        except ValueError:
            return None
    if isinstance(obj, dict):
        if isinstance(obj.get("workOrder"), dict):
            return obj["workOrder"]
        obj = list(obj.values())
    if isinstance(obj, list):
        return next((w for w in map(work_order, obj) if w), None)
    return None


def out(event, key, value, **extra):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event, key: value, **extra}}))


def main():
    data = json.load(sys.stdin)
    ev, session = data.get("hook_event_name"), data.get("session_id")
    if not session:
        return
    path = state_file(data)
    with state_lock(path):
        run_event(data, ev, session, path)


def run_event(data, ev, session, path):
    if ev == "SessionStart":
        if data.get("source") in ("compact", "clear", "resume"):
            for f in glob.glob(os.path.join(os.path.dirname(path), re.sub(r"[^A-Za-z0-9_-]", "_", session) + "-*")):
                os.remove(f)
            out("SessionStart", "additionalContext",
                "Context reset: pass contextReset: true on your next todo_claim so Dibs sends the rule texts again.")
        else:
            out("SessionStart", "additionalContext",
                f"Claude profile: {profile_name()} (CLAUDE_CONFIG_DIR={os.environ.get('CLAUDE_CONFIG_DIR') or '~/.claude'}). "
                "Quota warnings apply only when they name this profile.")
        return
    if ev == "PostToolUse":
        if data.get("tool_name") == "mcp__dibs__todo_claim":
            rules = (work_order(data.get("tool_response")) or {}).get("rules") or []
            with open(path, "a") as f:
                f.writelines(f"{r['id']}@{r['revision']}\n" for r in rules if r.get("text"))
        return
    triggers = load_triggers()
    ids = list(dict.fromkeys(i for k in match(data) for i in triggers.get(k, [])))
    rules, have = load_rules(), delivered(path)
    fresh = [i for i in ids if i in rules and f"{i}@{rules[i]['rev']}" not in have]
    new = [f"{i}@{rules[i]['rev']}" for i in fresh]
    parts = []
    if ev == "UserPromptSubmit":
        parts.append(REMINDER)
        profile = profile_name()
        pct = quota_pct(os.path.dirname(path), profile)
        if pct is not None and pct >= QUOTA_LIMIT and "quota-warned" not in have:
            new.append("quota-warned")
            parts.append(f"Quota at {int(pct)}% for profile {profile} (this session's own): rule 728. Start no new steps; park the work with a handoff.")
    body = "\n\n".join(f"[rule {i}] {rules[i]['text']}" for i in fresh)[:CAP]
    if body:
        parts.append(f"Rules for this action:\n\n{body}")
    bad = hyphen_labels(data) if ev == "PreToolUse" else []
    if bad:
        parts.append(f"Label names use spaces, not hyphens: {', '.join(bad)}.")
    if fresh and ev == "PreToolUse" and data.get("tool_use_id"):
        with open(path + ".calls", "a") as f:
            for i in fresh:
                f.write(json.dumps([data["tool_use_id"], f"{i}@{rules[i]['rev']}"]) + "\n")
    if new:
        with open(path, "a") as f:
            f.writelines(f"{n}\n" for n in new)
    if body and ev == "PreToolUse":
        parts.append(LATE)
    if parts:
        out(ev, "additionalContext", "\n\n".join(parts))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
