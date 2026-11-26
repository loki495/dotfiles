#!/usr/bin/env python3
"""Continuation link hook (UserPromptSubmit).

When the prompt names the session it continues (a /takeover command, a `Source session:` line, a
`Session:` line, and on the first prompt a Dibs handoff or plan checkpoint), tells Claude that
Sessioneer archives that source and starts a detached worker that runs
`sessioneer --replaces SOURCE --session <session_id> --json`, retrying while Sessioneer does not know
this session yet. A refusal is written to `<dir>/<session_id>.msg` and shown on the next prompt.
Never blocks: every path exits 0."""
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import time

ARCHIVE_TEXT = "Sessioneer archives it once it is idle and holds no claim; do not archive it yourself"
SESSION_LINE = re.compile(r"^Session:[ \t]*(\S+)[ \t]+(?:·[ \t]*)?(\S+)", re.M)
SOURCE_LINE = re.compile(r"^Source session:[ \t]*(\S+)(?:[ \t]+([^\s(]+))?[ \t]*\(", re.M)
SLASH_TAKEOVER = re.compile(r"\A\s*/takeover[ \t]+(\S+)((?:[ \t]+\S+){0,2})")
SKILL_TAKEOVER = re.compile(r"takeover skill for source[ \t]+(\S+)((?:[ \t]+\S+){0,2})")


def link_dir():
    if os.environ.get("CONTINUATION_LINK_DIR"):
        return os.environ["CONTINUATION_LINK_DIR"]
    if os.environ.get("XDG_RUNTIME_DIR"):
        return os.path.join(os.environ["XDG_RUNTIME_DIR"], "continuation-link")
    return f"/tmp/continuation-link-{os.getuid()}"


def safe_dir():
    """The directory when it is a real directory owned by us (made private), else None."""
    directory = link_dir()
    try:
        os.makedirs(directory, mode=0o700, exist_ok=True)
        info = os.lstat(directory)
    except OSError:
        return None
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        return None
    if info.st_mode & 0o077:
        os.chmod(directory, 0o700)
    return directory


def state_path(session_id, directory, suffix):
    return os.path.join(directory, re.sub(r"[^A-Za-z0-9_-]", "_", session_id) + suffix)


def prune(directory):
    cutoff = time.time() - 7 * 24 * 3600
    for name in os.listdir(directory):
        path = os.path.join(directory, name)
        info = os.lstat(path)
        if name.endswith((".msg", ".seen")) and stat.S_ISREG(info.st_mode) and info.st_mtime < cutoff:
            os.unlink(path)


def first_prompt(session_id, directory):
    """True when this call created the session's .seen marker; false when it existed or cannot be made."""
    if directory is None:
        return False
    try:
        prune(directory)
        fd = os.open(state_path(session_id, directory, ".seen"),
                     os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except OSError:
        return False
    os.close(fd)
    return True


def read_message(session_id, directory):
    if directory is None:
        return None
    path = state_path(session_id, directory, ".msg")
    if not os.path.lexists(path):
        return None
    try:
        with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW)) as f:
            text = f.read()
    except OSError:
        text = None
    try:
        os.unlink(path)
    except OSError:
        pass
    return text


def write_message(session_id, text):
    directory = safe_dir()
    if directory is None:
        return
    fd = os.open(state_path(session_id, directory, ".msg"),
                 os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(text)


def id_after_agent(rest):
    """The id among up to two tokens after the agent: an optional profile may come first."""
    tokens = rest.split()
    if not tokens:
        return None
    if len(tokens) == 1:
        return tokens[0]
    idlike = [t for t in tokens if re.search(r"[0-9-]", t)]
    return idlike[0] if len(idlike) == 1 else tokens[-1] if not idlike else idlike[0]


def takeover_source(prompt):
    match = SLASH_TAKEOVER.match(prompt)
    if match:
        return id_after_agent(match.group(2))
    match = SKILL_TAKEOVER.search(prompt)
    return id_after_agent(match.group(2)) if match else None


def source_line(prompt):
    match = SOURCE_LINE.search(prompt)
    return (match.group(2) or match.group(1)) if match else None


def session_line(text):
    match = SESSION_LINE.search(text)
    return match.group(2) if match else None


def dibs_show(*args):
    command = os.environ.get("DIBS_SHOW_CMD") or "docker exec -u www-data dibs-app php artisan todo:agent:show"
    try:
        proc = subprocess.run([*shlex.split(command), *args], capture_output=True, text=True, timeout=5)
        reply = json.loads(proc.stdout)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    return reply if proc.returncode == 0 and isinstance(reply, dict) else None


def handoff_source(prompt):
    match = re.search(r"\bhandoff\s+(?:in\s+Dibs\s+task\s+|task\s+)?#?(\d+)", prompt, re.I)
    if not match:
        return None
    task = dibs_show(match.group(1))
    if not task or "handoff" not in (task.get("labels") or []) or not isinstance(task.get("body"), str):
        return None
    return session_line(task["body"])


def plan_source(prompt):
    plan = re.search(r"\bplan\s+#?(\d+)", prompt, re.I)
    comment = re.search(r"\bcomment\s+#?(\d+)", prompt, re.I)
    if not plan or not comment:
        return None
    task = dibs_show(plan.group(1), "--all-comments")
    items = ((task or {}).get("comments") or {}).get("items")
    if not isinstance(items, list):
        return None
    for item in items:
        if isinstance(item, dict) and str(item.get("id")) == comment.group(1) and isinstance(item.get("body"), str):
            return session_line(item["body"])
    return None


def find_source(prompt, session_id, first):
    finders = [takeover_source, source_line, session_line]
    if first:
        finders += [handoff_source, plan_source]
    for finder in finders:
        source = finder(prompt)
        if source and source != session_id:
            return source
    return None


def env_float(name, default):
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return float(default)


def worker(source, session_id):
    binary = os.environ.get("SESSIONEER_BIN") or shutil.which("sessioneer") \
        or os.path.expanduser("~/www/personal/sessioneer/bin/sessioneer")
    retry = env_float("CONTINUATION_LINK_RETRY_SECONDS", "3")
    deadline = time.monotonic() + env_float("CONTINUATION_LINK_RETRY_LIMIT", "60")
    while True:
        try:
            proc = subprocess.run([binary, "--replaces", source, "--session", session_id, "--json"],
                                  capture_output=True, text=True, timeout=30)
            reply = json.loads(proc.stdout)
        except (OSError, ValueError, subprocess.SubprocessError):
            return
        if not isinstance(reply, dict) or reply.get("ok") is not False:
            return
        message = str(reply.get("message") or "refused")
        if "Unknown session" not in message:
            write_message(session_id, f"Continuation link to {source} was refused: {message}")
            return
        if time.monotonic() + retry >= deadline:
            return
        time.sleep(retry)


def main():
    if len(sys.argv) > 3 and sys.argv[1] == "--worker":
        worker(sys.argv[2], sys.argv[3])
        return
    data = json.load(sys.stdin)
    if not isinstance(data, dict):
        return
    session_id, prompt = data.get("session_id"), data.get("prompt")
    if not isinstance(session_id, str) or not session_id or not isinstance(prompt, str):
        return
    directory = safe_dir()
    parts = []
    message = read_message(session_id, directory)
    if message:
        parts.append(message)
    source = find_source(prompt, session_id, first_prompt(session_id, directory))
    if source:
        parts.append(f"This session continues {source}. {ARCHIVE_TEXT[0].upper()}{ARCHIVE_TEXT[1:]}.")
    if parts:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                                 "additionalContext": " ".join(parts)}}))
        sys.stdout.flush()
    if source:
        if os.environ.get("CONTINUATION_LINK_FOREGROUND") == "1":
            worker(source, session_id)
        else:
            subprocess.Popen([sys.executable, os.path.abspath(__file__), "--worker", source, session_id],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"continuation-link: {error}", file=sys.stderr)
    sys.exit(0)
