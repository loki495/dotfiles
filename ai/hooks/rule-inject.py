#!/usr/bin/env python3
"""Just-in-time rules: inject the few Dibs rule records an event is about, once per context lifetime.

One script for PreToolUse, PostToolUse, SessionStart and UserPromptSubmit. Rules come from the
exports ai/rules.md and ~/.dotfiles-private/ai/rules.private.md (RULE_FILES overrides, ':'-separated),
never from a live Dibs call. A rule is sent only if its id@revision is absent from the delivered set
$RULE_STATE_DIR (default $XDG_RUNTIME_DIR/dibs-rules, else ~/.cache/dibs-rules)/<session>-<agent_id|main>.
`git commit` and `git push` get their rules as context like any other command.
Everything else is plain additionalContext. Any failure is silent (exit 0): this hook never blocks
on its own trouble.
"""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
DEFAULT_FILES = [os.path.join(os.path.dirname(HERE), "rules.md"),
                 os.path.expanduser("~/.dotfiles-private/ai/rules.private.md")]
CAP = 9000  # additionalContext is capped at 10,000 characters
HEADING = re.compile(r"^## (\d+)@(\d+) (.*)$")

GIT = r"(^|[^\w-])git(\s+-\S+(\s+[^-\s]\S*)?)*\s+(%s)(\s|$)"
BASH = [  # (regex on the command, rule ids)
    (GIT % "commit", [732, 737, 738]),
    (GIT % "push", [734, 735, 730]),
    (GIT % "merge|rebase|worktree|cherry-pick|stash|reset", [731, 733, 736, 739]),
    (r"\b(pest|phpunit)\b", [740, 741, 742]),
    (r"\b(artisan|composer|pint|phpstan|rector)\b", [750]),
    (r"\bcurl\b", [745]),
    (r"\b(mysql|mariadb|sqlite3|tinker|migrate)\b", [929]),
    (r"\bsessioneer\s+--usage\b", [747]),
]
REMINDER = "Rule 1226: end your reply with one status line (Safe to archive this session. / Continue in this session: ... / Waiting on Andres: ... / All planned work is done.)."
TEST_FILE = re.compile(r"(^|/)tests?/|(^|/)test_|_test\.|\.test\.|\.spec\.|Test\.php$")
TOOLS = {  # tool name -> rule ids
    "Agent": [926, 1468], "Task": [926, 1468],
    "mcp__dibs__todo_create": [927, 748, 757],
    "mcp__dibs__todo_complete": [728, 730, 1209, 1307], "mcp__dibs__todo_release": [728, 729, 730],
    "mcp__dibs__todo_comment": [757, 1307], "mcp__dibs__todo_heartbeat": [1307],
    "mcp__playwright__browser_take_screenshot": [1310],
}


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
    """The rule ids the event is about."""
    ev, tool, inp = data.get("hook_event_name"), data.get("tool_name", ""), data.get("tool_input") or {}
    if ev == "UserPromptSubmit":
        return [928] if str(data.get("prompt", "")).startswith("[sessioneer peer:") else []
    if ev != "PreToolUse":
        return []
    if tool in TOOLS:
        return TOOLS[tool]
    if tool == "Bash":
        cmd, ids = str(inp.get("command", "")), []
        for rx, rule_ids in BASH:
            if re.search(rx, cmd):
                ids += [i for i in rule_ids if i not in ids]
        return ids
    path = str(inp.get("file_path") or inp.get("notebook_path") or "")
    if tool in ("Edit", "Write", "MultiEdit", "NotebookEdit") and path:
        ids = []
        if path.startswith(os.path.expanduser("~/www/")) and git_root_has_compose(path):
            ids += [745, 749]
        if TEST_FILE.search(path):
            ids += [740, 741, 742]
        if path.endswith(".md"):
            ids += [924, 737]
        if os.path.basename(path) in ("CLAUDE.md", "AGENTS.md"):
            ids += [925]
        return list(dict.fromkeys(ids))
    return []


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
    if ev == "SessionStart":
        if data.get("source") in ("compact", "clear", "resume"):
            for f in glob.glob(os.path.join(os.path.dirname(path), re.sub(r"[^A-Za-z0-9_-]", "_", session) + "-*")):
                os.remove(f)
            out("SessionStart", "additionalContext",
                "Context reset: pass contextReset: true on your next todo_claim so Dibs sends the rule texts again.")
        return
    if ev == "PostToolUse":
        if data.get("tool_name") == "mcp__dibs__todo_claim":
            rules = (work_order(data.get("tool_response")) or {}).get("rules") or []
            with open(path, "a") as f:
                f.writelines(f"{r['id']}@{r['revision']}\n" for r in rules if r.get("text"))
        return
    ids = match(data)
    rules, have = load_rules(), delivered(path)
    fresh = [i for i in ids if i in rules and f"{i}@{rules[i]['rev']}" not in have]
    if fresh:
        with open(path, "a") as f:
            f.writelines(f"{i}@{rules[i]['rev']}\n" for i in fresh)
    body = "\n\n".join(f"[rule {i}] {rules[i]['text']}" for i in fresh)[:CAP]
    if ev == "UserPromptSubmit":
        body = REMINDER + (f"\n\nRules for this action:\n\n{body}" if body else "")
    elif body:
        body = f"Rules for this action:\n\n{body}"
    if body:
        out(ev, "additionalContext", body)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
