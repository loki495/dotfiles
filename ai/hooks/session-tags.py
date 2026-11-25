#!/usr/bin/env python3
"""Session tags hook (rule 2302), two events.

SessionStart (startup, resume): starts a detached worker and prints nothing, because a session's own
`sessioneer --show` can block while it launches. The worker waits until Sessioneer tracks the session,
adds the `project <name>` tag (and `worker` when the title says so), and writes any message (a failed
add, or a missing role tag) to `<dir>/<session_id>.msg`. SESSION_TAGS_FOREGROUND=1 runs it inline.

UserPromptSubmit: prints that file as additionalContext and deletes it; never calls Sessioneer."""
import json
import os
import re
import shutil
import subprocess
import sys
import time

ROLES = {"worker", "orchestrator", "curator", "handoff receiver", "designer", "test builder",
         "implementer", "runner", "interpreter", "reviewer", "closer", "interactive"}
ROLE_TAIL = ("No role tag: add one with `sessioneer --tag-add <role>`: worker, orchestrator, curator, "
             "handoff receiver, a persona name, or interactive when Andres drives this session (rule 2302).")


def run(argv, timeout=5):
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout)


def sessioneer(binary, *args, timeout=5):
    """Return (reply dict or None, completed process or None)."""
    try:
        proc = run([binary, *args], timeout)
    except (OSError, subprocess.SubprocessError):
        return None, None
    try:
        reply = json.loads(proc.stdout)
    except ValueError:
        return None, proc
    if not isinstance(reply, dict) or proc.returncode != 0 or reply.get("ok") is not True:
        return (reply if isinstance(reply, dict) else None), proc
    return reply, proc


def read_record(binary, target):
    reply, proc = sessioneer(binary, "--show", target, "--json", timeout=2)
    ok = proc is not None and proc.returncode == 0 and reply and reply.get("ok") is True
    return reply if ok else None


def project_tag(directory):
    if not directory:
        return None
    try:
        proc = run(["git", "-C", directory, "rev-parse", "--path-format=absolute", "--git-common-dir"])
    except (OSError, subprocess.SubprocessError):
        return None
    common = proc.stdout.strip().rstrip("/")
    if proc.returncode != 0 or not common:
        return None
    if common.endswith("/.git"):
        name = os.path.basename(os.path.dirname(common))
    else:
        name = os.path.basename(common).removesuffix(".git")
    name = re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()[:24].strip()
    return f"project {name}" if name else None


def is_worker_title(title):
    title = title if isinstance(title, str) else ""
    title = title.removeprefix("Session name: ")
    return title.lower().startswith("[worker]")


def add_error(reply, proc):
    for value in ((reply or {}).get("error"), (reply or {}).get("message"),
                  proc.stderr.strip() if proc else ""):
        if value:
            return str(value)
    return f"exit {proc.returncode}" if proc else "no reply"


def env_float(name, default):
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return float(default)


def msg_dir():
    if os.environ.get("SESSION_TAGS_DIR"):
        return os.environ["SESSION_TAGS_DIR"]
    if os.environ.get("XDG_RUNTIME_DIR"):
        return os.path.join(os.environ["XDG_RUNTIME_DIR"], "session-tags")
    return f"/tmp/session-tags-{os.getuid()}"


def msg_file(data):
    session_id = data.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        return None
    return os.path.join(msg_dir(), re.sub(r"[^A-Za-z0-9_-]", "_", session_id) + ".msg")


def write_message(data, message):
    directory = msg_dir()
    os.makedirs(directory, exist_ok=True)
    cutoff = time.time() - 24 * 3600
    for name in os.listdir(directory):
        path = os.path.join(directory, name)
        if name.endswith(".msg") and os.path.getmtime(path) < cutoff:
            os.unlink(path)
    path = msg_file(data)
    if message and path:
        with open(path, "w") as f:
            f.write(message)


def read_until_ready(binary, target):
    end = time.monotonic() + env_float("SESSION_TAGS_READY", "60")
    while True:
        record = read_record(binary, target)
        if record is not None or time.monotonic() >= end:
            return record
        time.sleep(0.5)


def worker(data):
    source = data.get("source")
    target = os.environ.get("SESSIONEER_SELF") or data.get("session_id")
    binary = os.environ.get("SESSIONEER_BIN") or shutil.which("sessioneer")
    if not target or not binary:
        return

    record = read_until_ready(binary, target)
    if record is None:
        return
    if source == "startup" and not record.get("tags"):
        end = time.monotonic() + env_float("SESSION_TAGS_WAIT", "3")
        while not record.get("tags") and time.monotonic() < end:
            time.sleep(min(0.5, max(0, end - time.monotonic())))
            record = read_record(binary, target) or record

    tags = [t for t in (record.get("tags") or []) if isinstance(t, str)]
    new = []
    if not any(t == "project" or t.startswith("project ") for t in tags):
        project = project_tag(data.get("cwd") or record.get("workdir"))
        if project:
            new.append(project)
    role_known = bool(ROLES & set(tags))
    if not role_known and is_worker_title(record.get("title")):
        new.append("worker")
        role_known = True

    parts = []
    if new:
        joined = ",".join(new)
        reply, proc = sessioneer(binary, "--tag-add", joined, "--session", target, "--json")
        if reply and reply.get("ok") is True and proc.returncode == 0:
            if isinstance(reply.get("tags"), list):
                tags = [t for t in reply["tags"] if isinstance(t, str)]
        else:
            parts.append(f"Session tags: could not add {joined}: {add_error(reply, proc)}. "
                         "Add them with sessioneer --tag-add (rule 2302).")
    if not role_known:
        parts.append(f"Session tags: {', '.join(tags) or 'none'}. {ROLE_TAIL}")
    write_message(data, " ".join(parts))


def deliver(data):
    path = msg_file(data)
    if not path or not os.path.exists(path):
        return
    with open(path) as f:
        text = f.read()
    os.unlink(path)
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                             "additionalContext": text}}))


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--worker":
        worker(json.loads(sys.argv[2]))
        return
    data = json.load(sys.stdin)
    if not isinstance(data, dict):
        return
    event = data.get("hook_event_name")
    if event == "UserPromptSubmit":
        deliver(data)
    elif event == "SessionStart" and data.get("source") in ("startup", "resume"):
        if os.environ.get("SESSION_TAGS_FOREGROUND") == "1":
            worker(data)
        else:
            subprocess.Popen([sys.executable, os.path.abspath(__file__), "--worker", json.dumps(data)],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
