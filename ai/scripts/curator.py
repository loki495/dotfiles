#!/usr/bin/env python3
"""Unattended Dibs curator: an idle-gated, quota-aware run of one pass with a Dibs claim and report.

A pass file (ai/curator/passes/<name>.md) holds `Key: value` headers, a `---` line and the prompt body;
ai/curator/base.md is prepended to every prompt. The gate skips when another run holds the lock, the
pass ran recently, a Sessioneer session is active, agent transcripts changed recently, the pass
precheck fails, or no candidate has quota. A run claims the standing issue `Curator runs`, launches
`claude -p` bound to Dibs only (plus Read/Grep/Glob on paths under TOOL_PATHS), checks the model from the
init and assistant events, polls quota, posts one report comment and releases. SIGTERM and SIGINT stop
the agent's process group, then report and release (outcome `stopped by signal`, exit 3). The lock file
holds `pid start deadline` while a run is live and is truncated on release.

Usage:
  curator.py run --pass NAME [--dry-run]    exit 0 ran ok/skipped/parked, 2 config, Dibs or curator error, 3 run not ok
  curator.py gate --pass NAME [--json]      read-only; exit 0 would run, 1 would skip

Environment overrides: CURATOR_HOME, CURATOR_STATE_DIR, CURATOR_SESSIONEER, DIBS_CLI, CURATOR_CLAUDE,
SESSION_FLOW_THRESHOLDS, CURATOR_ACTIVITY_PATHS, QUOTA_GO_MAX, QUOTA_PARK.
"""
import argparse
import datetime
import fcntl
import json
import math
import os
import re
import selectors
import shlex
import signal
import subprocess
import sys
import time
import traceback
import uuid

LIVENESS_NOTE = "Note: process liveness could not be verified in this environment (weaker-assurance claim)."
TIERS = ("mechanical", "balanced", "advanced")
RUNS_TITLE = "Curator runs"
PROPOSALS_TITLE = "Curator proposals"
TOOL_RE = re.compile(r"^(Read|Grep|Glob)\(//([^\s()*]+)/\*\*\)$")
MCP_RE = re.compile(r"^mcp__dibs__\w+$")
PASS_RE = re.compile(r"^[A-Za-z0-9_-]+$")
PLACEHOLDERS = ("run_id", "pass", "runs_issue", "proposals_issue", "last_ok", "model")


class ConfigError(Exception):
    pass


class DibsError(Exception):
    pass


class StopRun(Exception):
    """SIGTERM or SIGINT arrived during a run."""


class DibsExit(DibsError):
    """The Dibs command exited non-zero."""


def say(text):
    print(text, flush=True)


def home():
    return os.path.expanduser("~")


def split_cmd(env_name, default):
    return shlex.split(os.environ.get(env_name) or default)


def read_keyvalues(path):
    values = {}
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except OSError as e:
        raise ConfigError(f"cannot read {path}: {e}")
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def number(text, label, minimum=0.0, allow_equal=False):
    try:
        value = float(text)
    except (TypeError, ValueError):
        raise ConfigError(f"{label}: not a number: {text!r}")
    if not math.isfinite(value) or value < minimum or (value == minimum and not allow_equal):
        raise ConfigError(f"{label}: out of range: {text!r}")
    return value


def load_config():
    curator_home = os.path.expanduser(os.environ.get("CURATOR_HOME") or "~/dotfiles/ai/curator")
    raw = {"ACTIVE_MIN": "30", "ACTIVITY_PATHS": "", "QUOTA_MAX_AGE_MIN": "60", "QUOTA_POLL_SEC": "300",
           "HEARTBEAT_SEC": "600", "LOG_DAYS": "14", "LOG_KEEP": "200", "DIBS_AREA": "2",
           "DIBS_GROUP": "AI workflows", "TOOL_PATHS": "~/www:~/dotfiles"}
    raw.update(read_keyvalues(os.path.join(curator_home, "curator.conf")))
    cfg = {
        "home": curator_home,
        "state": os.path.expanduser(os.environ.get("CURATOR_STATE_DIR") or "~/.local/state/curator"),
        "active_min": number(raw["ACTIVE_MIN"], "ACTIVE_MIN"),
        "quota_max_age_min": number(raw["QUOTA_MAX_AGE_MIN"], "QUOTA_MAX_AGE_MIN"),
        "quota_poll_sec": number(raw["QUOTA_POLL_SEC"], "QUOTA_POLL_SEC"),
        "heartbeat_sec": number(raw["HEARTBEAT_SEC"], "HEARTBEAT_SEC"),
        "log_days": number(raw["LOG_DAYS"], "LOG_DAYS"),
        "log_keep": int(number(raw["LOG_KEEP"], "LOG_KEEP", 0, True)),
        "area": str(int(number(raw["DIBS_AREA"], "DIBS_AREA"))),
        "group": raw["DIBS_GROUP"],
    }
    paths = os.environ["CURATOR_ACTIVITY_PATHS"] if "CURATOR_ACTIVITY_PATHS" in os.environ else raw["ACTIVITY_PATHS"]
    cfg["tool_dirs"] = [os.path.realpath(os.path.expanduser(d)) for d in raw["TOOL_PATHS"].split(":") if d]
    if "/" in cfg["tool_dirs"]:
        raise ConfigError("TOOL_PATHS must not contain the filesystem root")
    cfg["activity_paths"] = [os.path.expanduser(p) for p in paths.split(":") if p]
    thresholds = read_keyvalues(os.path.expanduser(
        os.environ.get("SESSION_FLOW_THRESHOLDS") or "~/dotfiles/ai/skills/session-flow/thresholds.conf"))
    for name in ("QUOTA_GO_MAX", "QUOTA_PARK"):
        cfg[name.lower()] = number(os.environ.get(name) or thresholds.get(name), name, 0, True)
    cfg["candidates"] = load_candidates(os.path.join(curator_home, "candidates.txt"))
    try:
        cfg["base"] = open(os.path.join(curator_home, "base.md"), encoding="utf-8").read()
    except OSError as e:
        raise ConfigError(f"cannot read base.md: {e}")
    return cfg


def load_candidates(path):
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except OSError as e:
        raise ConfigError(f"cannot read {path}: {e}")
    found = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) != 5:
            raise ConfigError(f"candidates.txt: expected 5 fields: {line!r}")
        found.append(dict(zip(("tier", "agent", "profile", "model", "effort"), fields)))
    return found


def load_pass(cfg, name):
    if not PASS_RE.match(name):
        raise ConfigError(f"bad pass name: {name!r}")
    path = os.path.join(cfg["home"], "passes", name + ".md")
    try:
        lines = open(path, encoding="utf-8").read().split("\n")
    except OSError as e:
        raise ConfigError(f"cannot read pass file: {e}")
    if "---" not in lines:
        raise ConfigError(f"{name}: missing --- line")
    end = lines.index("---")
    headers = {}
    for line in lines[:end]:
        if not line.strip():
            continue
        if ":" not in line:
            raise ConfigError(f"{name}: bad header line: {line!r}")
        key, value = line.split(":", 1)
        headers[key.strip()] = value.strip()
    if headers.get("Tier") not in TIERS:
        raise ConfigError(f"{name}: Tier must be one of {', '.join(TIERS)}")
    tools = [t.strip() for t in headers.get("Tools", "").split(",")] if headers.get("Tools") else []
    tool_dirs = []
    for tool in tools:
        match = TOOL_RE.match(tool)
        if ".." in tool or not (match or MCP_RE.match(tool)):
            raise ConfigError(f"{name}: tool not allowed: {tool!r}")
        if match:
            path = os.path.realpath("/" + match.group(2))
            if not any(path == d or path.startswith(d + "/") for d in cfg["tool_dirs"]):
                raise ConfigError(f"{name}: tool path outside TOOL_PATHS: {tool!r}")
            if path not in tool_dirs:
                tool_dirs.append(path)
    precheck = shlex.split(headers["Precheck"]) if headers.get("Precheck") else None
    if headers.get("Precheck") is not None and headers["Precheck"] and not precheck:
        raise ConfigError(f"{name}: empty Precheck")
    return {
        "name": name,
        "tier": headers["Tier"],
        "timeout_min": number(headers.get("Timeout-min", "30"), "Timeout-min"),
        "budget": number(headers.get("Budget-usd", "1"), "Budget-usd"),
        "min_interval": number(headers.get("Min-interval-min", "0"), "Min-interval-min", 0, True),
        "tools": tools,
        "tool_dirs": tool_dirs,
        "precheck": precheck,
        "body": "\n".join(lines[end + 1:]),
    }


def last_path(cfg, p):
    return os.path.join(cfg["state"], f"last-{p['name']}.json")


def read_last(cfg, p):
    try:
        doc = json.load(open(last_path(cfg, p)))
        return doc if isinstance(doc, dict) else {}
    except (OSError, ValueError):
        return {}


def write_last(cfg, p, outcome, ok_at):
    doc = {"finished_at": int(time.time()), "outcome": outcome, "ok_at": ok_at}
    path = last_path(cfg, p)
    with open(path + ".tmp", "w") as f:
        json.dump(doc, f)
    os.replace(path + ".tmp", path)


# Lock

def pid_cmdline(pid):
    try:
        return open(f"/proc/{pid}/cmdline", "rb").read().decode(errors="replace").split("\0")
    except OSError:
        return []


def try_flock(f):
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except BlockingIOError:
        return False


def wait_for_lock(f, seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if try_flock(f):
            return True
        time.sleep(0.1)
    return try_flock(f)


def process_start(pid):
    """Epoch second the process started, from /proc, or None."""
    try:
        fields = open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split()
        boot = next(int(l.split()[1]) for l in open("/proc/stat") if l.startswith("btime"))
        return boot + int(fields[19]) / os.sysconf("SC_CLK_TCK")
    except (OSError, IndexError, ValueError, StopIteration):
        return None


def is_stale_holder(f):
    """Past its own deadline, running curator.py, and started no later than the lock file says."""
    try:
        pid, start, deadline = (int(x) for x in open(f.name).read().split()[:3])
    except (OSError, ValueError):
        return None
    argv = pid_cmdline(pid)
    began = process_start(pid)
    if (pid == os.getpid() or time.time() <= deadline or len(argv) < 2
            or os.path.basename(argv[1]) != "curator.py" or began is None or began > start + 2):
        return None
    return pid


def kill_stale_holder(f):
    pid = is_stale_holder(f)
    if pid is None:
        return False
    try:
        group = os.getpgid(pid)
        if group == os.getpgrp():
            return False
        say(f"killing stale curator holder {pid}")
        os.killpg(group, signal.SIGTERM)
        if wait_for_lock(f, 10):
            return True
        os.killpg(group, signal.SIGKILL)
    except ProcessLookupError:
        pass
    return wait_for_lock(f, 5)


def take_lock(cfg, p):
    """Return (lock file or None, reason). The gate command only probes and never kills."""
    return _lock(cfg, p, take=True)


def probe_lock(cfg, p):
    return _lock(cfg, p, take=False)


def _lock(cfg, p, take):
    path = os.path.join(cfg["state"], "curator.lock")
    if take:
        os.makedirs(cfg["state"], exist_ok=True)
    elif not os.path.exists(path):
        return None, None
    f = open(path, "a+")
    if not try_flock(f) and not (take and kill_stale_holder(f)):
        f.close()
        return None, "already running"
    if not take:
        f.close()
        return None, None
    f.seek(0)
    f.truncate()
    start = int(time.time())
    f.write(f"{os.getpid()} {start} {start + int(p['timeout_min'] * 60) + 600}\n")
    f.flush()
    return f, None


# Gate checks

def run_json(cmd, timeout=60):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    try:
        return json.loads(out.stdout)
    except ValueError:
        return None


def sessioneer_cmd(*args):
    return split_cmd("CURATOR_SESSIONEER", "sessioneer") + list(args)


def session_reason():
    doc = run_json(sessioneer_cmd("--list", "--json"))
    if not isinstance(doc, dict) or doc.get("ok") is not True or not isinstance(doc.get("sessions"), list):
        return "sessioneer unavailable"
    for s in doc["sessions"]:
        if not isinstance(s, dict) or not isinstance(s.get("name"), str):
            return "sessioneer unavailable"
        tags = s.get("tags") if isinstance(s.get("tags"), list) else []
        if "curator" in tags or s["name"].startswith("[curator]"):
            continue
        if s.get("status") not in ("idle", "blocked"):
            return f"session active: {s['name']} ({s.get('status')})"
    return None


def activity_reason(cfg):
    newest = 0.0
    for root_path in cfg["activity_paths"]:
        for root, _dirs, files in os.walk(root_path):
            for name in files:
                try:
                    newest = max(newest, os.stat(os.path.join(root, name)).st_mtime)
                except OSError:
                    continue
    age = (time.time() - newest) / 60
    if newest and age < cfg["active_min"]:
        return f"recent activity: newest file is {round(age)} min old"
    return None


def precheck_result(p):
    """0 = work, 1 = nothing to do, 2 = failed."""
    try:
        rc = subprocess.run(p["precheck"], capture_output=True, timeout=120, stdin=subprocess.DEVNULL).returncode
    except (OSError, subprocess.TimeoutExpired):
        return 2
    return rc if rc in (0, 1) else 2


def parse_time(text):
    when = datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
    if when.tzinfo is None:
        raise ValueError("no timezone")
    return when


def profile_quota(usage, cand, max_age_min):
    """Return (pct or None, resets_at list, problem or None). max_age_min None skips the freshness check."""
    try:
        profile = usage["agents"][cand["agent"]]["profiles"][cand["profile"]]
    except (KeyError, TypeError):
        return None, [], "profile missing"
    if not isinstance(profile, dict):
        return None, [], "profile unreadable"
    try:
        quota = profile["quota"]
        resets = [quota[k]["resets_at"] for k in ("session", "week_all") if quota[k].get("resets_at")]
    except (KeyError, TypeError, AttributeError):
        quota, resets = None, []
    if profile.get("ok") is not True:
        return None, resets, "profile not ok"
    try:
        values = [quota[k]["pct"] for k in ("session", "week_all")]
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 <= v <= 100 for v in values):
            raise ValueError("bad pct")
        if max_age_min is not None:
            age = time.time() - parse_time(quota["captured_at"]).timestamp()
            if not 0 <= age <= max_age_min * 60:
                return None, resets, "quota stale"
    except (KeyError, TypeError, ValueError, AttributeError):
        return None, resets, "quota unknown"
    return max(values), resets, None


def fetch_usage():
    return run_json(sessioneer_cmd("--usage"))


def earliest(times):
    parsed = []
    for t in times:
        try:
            parsed.append((parse_time(t), t))
        except (ValueError, AttributeError):
            continue
    return min(parsed)[1] if parsed else None


def choose_candidate(cfg, p):
    """Return (candidate, pct, None) or (None, None, parked reason)."""
    usage = fetch_usage()
    reasons, resets = [], []
    for cand in cfg["candidates"]:
        if cand["tier"] != p["tier"]:
            continue
        label = f"{cand['agent']} {cand['profile']} {cand['model']}"
        if cand["agent"] != "claude":
            reasons.append(f"{label}: no adapter for {cand['agent']}")
            continue
        pct, found, problem = profile_quota(usage, cand, cfg["quota_max_age_min"])
        resets += found
        if problem:
            reasons.append(f"{label}: {problem}")
        elif pct >= cfg["quota_go_max"]:
            reasons.append(f"{label}: quota {round(pct)}% at or above {cfg['quota_go_max']:g}%")
        else:
            return cand, pct, None
    reason = "parked: no candidate with quota"
    if not reasons:
        reasons.append(f"no candidate for tier {p['tier']}")
    reason += " (" + "; ".join(reasons)
    soonest = earliest(resets)
    return None, None, reason + (f"; earliest reset {soonest}" if soonest else "") + ")"


def decide(cfg, p, lock_taker):
    """Run the gate checks in order. Returns a decision dict; 'lock' holds the lock file when taken."""
    d = {"run": False, "reason": "", "candidate": None, "kind": "skip", "lock": None, "pct": None}
    lock, reason = lock_taker(cfg, p)
    if reason:
        d["reason"] = reason
        return d
    d["lock"] = lock
    last = read_last(cfg, p)
    ok_at = last.get("ok_at")
    if isinstance(ok_at, (int, float)) and time.time() - ok_at < p["min_interval"] * 60:
        d["reason"] = "ran recently"
        return d
    reason = session_reason() or activity_reason(cfg)
    if reason:
        d["reason"] = reason
        return d
    if p["precheck"]:
        result = precheck_result(p)
        if result == 2:
            d["reason"] = "precheck failed"
            return d
        if result == 1:
            d.update(reason="nothing to do", kind="nothing")
            return d
    cand, pct, parked = choose_candidate(cfg, p)
    if not cand:
        d.update(reason=parked, kind="parked")
        return d
    d.update(run=True, reason=f"would run {cand['agent']} {cand['profile']} {cand['model']} {cand['effort']}",
             candidate=cand, kind="go", pct=pct)
    return d


def release_lock(d):
    if d["lock"]:
        d["lock"].seek(0)
        d["lock"].truncate()
        d["lock"].close()
        d["lock"] = None


# Dibs

def dibs(*args):
    cmd = split_cmd("DIBS_CLI", "docker exec -u www-data dibs-app php artisan") + [str(a) for a in args]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise DibsError(f"{args[0]}: {e}")
    if out.returncode != 0:
        raise DibsExit(f"{args[0]} exited {out.returncode}: {out.stderr.strip()[:200]}")
    text = out.stdout.lstrip()
    try:
        value, end = json.JSONDecoder().raw_decode(text)
    except ValueError:
        raise DibsError(f"{args[0]}: output is not JSON")
    if text[end:].strip() not in ("", LIVENESS_NOTE):
        raise DibsError(f"{args[0]}: unexpected trailing output")
    return value


def open_tasks():
    doc = dibs("todo:agent:list")
    if not isinstance(doc, dict) or not isinstance(doc.get("tasks"), list):
        raise DibsError("todo:agent:list: unexpected shape")
    return doc["tasks"]


def find_standing(tasks, title):
    matches = [t["id"] for t in tasks if t.get("title") == title and t.get("state") == "OPEN"]
    if len(matches) > 1:
        raise ConfigError(f"more than one open issue titled {title!r}: {matches}")
    return matches[0] if matches else None


def standing_issues(cfg, create):
    tasks = open_tasks()
    ids = []
    for title, key, purpose in ((RUNS_TITLE, "curator:runs", "Claimed by each curator run, which posts its report here."),
                                (PROPOSALS_TITLE, "curator:proposals", "Parent of the curator's proposal tasks.")):
        found = find_standing(tasks, title)
        if found is None and create:
            made = dibs("todo:agent:create", title, "--body", purpose, "--area", cfg["area"], "--new-group",
                        cfg["group"], "--new-label", "curator", "--idempotency-key", key)
            found = made["id"] if isinstance(made, dict) else None
            if not isinstance(found, int):
                raise DibsError("todo:agent:create: no id")
        ids.append(found)
    return ids


def rule_snapshot():
    return {t["id"]: (t.get("state"), t.get("modifiedAt")) for t in open_tasks() if "rule" in t.get("labels", [])}


def changed_ids(before, after):
    return sorted(i for i in set(before) | set(after) if before.get(i) != after.get(i))


# Agent

def render(text, values):
    for key in PLACEHOLDERS:
        text = text.replace("{" + key + "}", str(values[key]))
    return text


def agent_command(p, cand, session_id):
    built_in = []
    for tool in p["tools"]:
        name = tool.split("(")[0]
        if tool.startswith(("Read(", "Grep(", "Glob(")) and name not in built_in:
            built_in.append(name)
    mcp = {"mcpServers": {"dibs": {"type": "stdio", "command": f"{home()}/dotfiles/ai/scripts/claude-dibs-mcp.py",
                                   "args": []}}}
    return split_cmd("CURATOR_CLAUDE", "claude") + [
        "-p", "--model", cand["model"], "--effort", cand["effort"], "--session-id", session_id,
        "--no-session-persistence", "--restricted", "--strict-mcp-config", "--mcp-config", json.dumps(mcp),
        "--permission-mode", "dontAsk", "--tools", ",".join(built_in),
        "--allowed-tools", ",".join(["mcp__dibs"] + p["tools"]), "--max-budget-usd", str(p["budget"]),
        "--output-format", "stream-json", "--verbose"] + [a for d in p["tool_dirs"] for a in ("--add-dir", d)]


def agent_env(cand):
    env = {"HOME": home(), "PATH": f"{home()}/.local/bin:/usr/local/bin:/usr/bin",
           "DIBS_LESSON_PROMPT": "off", "DIBS_STOP_GATE": "off"}
    if cand["profile"] == "work":
        env["CLAUDE_CONFIG_DIR"] = f"{home()}/.claude-work"
    return env


def terminate(proc):
    """TERM to the process group and wait 20 s; the caller then kills what is left."""
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=20)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        pass


def kill_group(proc):
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.wait()


def watch(cfg, p, cand, proc, log, token, runs_issue):
    """Read the stream until the agent ends or a limit stops it. Returns (outcome or None, result event, init model seen)."""
    sel = selectors.DefaultSelector()
    sel.register(proc.stdout, selectors.EVENT_READ)
    fd = proc.stdout.fileno()
    now = time.monotonic()
    deadline = now + p["timeout_min"] * 60
    next_poll, next_beat = now + cfg["quota_poll_sec"], now + cfg["heartbeat_sec"]
    outcome, result, init_seen, buf = None, None, False, b""

    while outcome is None:
        events = sel.select(0.2)
        if events:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf and outcome is None:
                raw, buf = buf.split(b"\n", 1)
                line = raw.decode(errors="replace")
                log.write(line + "\n")
                log.flush()
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(event, dict):
                    continue
                model = event.get("model") if event.get("subtype") == "init" else None
                if event.get("type") == "assistant" and isinstance(event.get("message"), dict):
                    model = event["message"].get("model")
                if model is not None and model != "<synthetic>":
                    if model != cand["model"]:
                        outcome = f"model mismatch: {model}"
                    elif event.get("subtype") == "init":
                        init_seen = True
                if event.get("type") == "result":
                    result = event
        elif proc.poll() is not None:
            break
        now = time.monotonic()
        if outcome is None and now > deadline:
            outcome = "timeout"
        if outcome is None and now >= next_poll:
            next_poll = now + cfg["quota_poll_sec"]
            pct, _resets, _problem = profile_quota(fetch_usage(), cand, None)
            if pct is not None and pct >= cfg["quota_park"]:
                outcome = f"parked at quota {round(pct)}%"
        if outcome is None and now >= next_beat:
            next_beat = now + cfg["heartbeat_sec"]
            try:
                dibs("todo:agent:heartbeat", runs_issue, "--pid", os.getpid(), "--token", token,
                     "--minutes", math.ceil(p["timeout_min"] + 15))
            except DibsError as e:
                say(f"heartbeat failed: {e}")
    sel.close()
    return outcome, result, init_seen


def run_agent(cfg, p, cand, prompt, session_id, token, runs_issue, log_path, err_path):
    """Launch and watch the agent. Returns a dict with outcome, result event, verified model, other models."""
    info = {"outcome": None, "result": None, "verified": None, "others": []}
    work = os.path.join(cfg["state"], "work")
    os.makedirs(work, exist_ok=True)
    with open(log_path, "w") as log, open(err_path, "w") as err:
        try:
            proc = subprocess.Popen(agent_command(p, cand, session_id), cwd=work, env=agent_env(cand),
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=err,
                                    start_new_session=True)
        except OSError as e:
            info["outcome"] = f"agent error: {e}"
            return info
        outcome, result, init_seen = None, None, False
        try:
            try:
                proc.stdin.write(prompt.encode())
                proc.stdin.close()
            except OSError:
                pass
            outcome, result, init_seen = watch(cfg, p, cand, proc, log, token, runs_issue)
            if outcome is None:
                try:
                    proc.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    outcome = "agent error: did not exit"
        finally:
            if proc.poll() is None:
                terminate(proc)
            kill_group(proc)
    usage = result.get("modelUsage") if result and isinstance(result.get("modelUsage"), dict) else {}
    for model in sorted(k for k in usage if k != cand["model"]):
        cost = usage[model].get("costUSD") if isinstance(usage[model], dict) else None
        info["others"].append(f"{model} ${cost:.2f}" if isinstance(cost, (int, float)) else f"{model} $?")
    if outcome is None:
        outcome = "agent error" if result is None or result.get("is_error") else "ok"
    if outcome == "ok" and not init_seen:
        outcome = "model not verified"
    info.update(outcome=outcome, result=result, verified=cand["model"] if init_seen else None)
    return info


# Run

def report_text(run_id, p, cand, started, took, info, quota, rules, log_paths):
    result = info["result"] or {}
    cost = result.get("total_cost_usd")
    cost = f"${cost:.2f}" if isinstance(cost, (int, float)) else "?"
    turns = result.get("num_turns")
    turns = turns if isinstance(turns, int) else "?"
    summary = result.get("result") if isinstance(result.get("result"), str) else "(none)"
    began = datetime.datetime.fromtimestamp(started).astimezone().isoformat(timespec="seconds")
    return (
        f"Curator run {run_id}: {p['name']} pass, {info['outcome']}.\n"
        f"- Started {began}, took {int(took) // 60}m{int(took) % 60}s.\n"
        f"- Agent: {cand['agent']} {cand['profile']} {cand['model']} {cand['effort']}; "
        f"verified model: {info['verified'] or 'not verified'}.\n"
        f"- Cost: {cost} over {turns} turns; quota {quota[0]} to {quota[1]}.\n"
        f"- Other models in usage: {', '.join(info['others']) or 'none'}.\n"
        f"- Rule records changed: {', '.join(map(str, rules)) if rules else 'none'}.\n"
        f"- Log: {log_paths[0]} and {log_paths[1]}.\n\n"
        f"Pass summary:\n{summary[:1500]}")


def pct_text(pct):
    return "?" if pct is None else f"{round(pct)}%"


def prune_runs(cfg):
    runs = os.path.join(cfg["state"], "runs")
    os.makedirs(runs, exist_ok=True)
    files = []
    for name in os.listdir(runs):
        path = os.path.join(runs, name)
        if os.path.isfile(path):
            files.append((os.stat(path).st_mtime, path))
    files.sort(reverse=True)
    cutoff = time.time() - cfg["log_days"] * 86400
    for rank, (mtime, path) in enumerate(files):
        if mtime < cutoff or rank >= cfg["log_keep"]:
            os.unlink(path)


def build_prompt(cfg, p, cand, run_id, runs_issue, proposals_issue, last):
    ok_at = last.get("ok_at")
    last_ok = "never"
    if isinstance(ok_at, (int, float)):
        last_ok = datetime.datetime.fromtimestamp(ok_at).astimezone().isoformat(timespec="seconds")
    values = {"run_id": run_id, "pass": p["name"], "runs_issue": runs_issue, "proposals_issue": proposals_issue,
              "last_ok": last_ok, "model": cand["model"]}
    return render(cfg["base"] + "\n" + p["body"], values)


def do_run(cfg, p, d, run_id):
    cand = d["candidate"]
    last = read_last(cfg, p)
    runs_issue, proposals_issue = standing_issues(cfg, create=True)
    session_id = str(uuid.uuid4())
    prompt = build_prompt(cfg, p, cand, run_id, runs_issue, proposals_issue, last)
    agent = f"curator:curator {p['name']} {run_id}:{session_id}"
    minutes = math.ceil(p["timeout_min"] + 15)
    try:
        claim = dibs("todo:agent:claim", runs_issue, "--agent", agent, "--pid", os.getpid(), "--minutes", minutes)
        token = claim["capability_token"]
    except DibsExit:
        say(f"skip: claim refused on issue {runs_issue}")
        return 0
    except (DibsError, KeyError, TypeError) as e:
        raise DibsError(f"claim: {e}")
    info = {"outcome": "dibs error", "result": None, "verified": None, "others": []}
    started = time.time()
    runs_dir = os.path.join(cfg["state"], "runs")
    log_paths = (os.path.join(runs_dir, f"{run_id}.jsonl"), os.path.join(runs_dir, f"{run_id}.stderr"))
    before = []

    def launch():
        os.makedirs(runs_dir, exist_ok=True)
        before.append(rule_snapshot())
        say(f"launching {cand['agent']} {cand['profile']} {cand['model']} {cand['effort']} for run {run_id}")
        info.update(run_agent(cfg, p, cand, prompt, session_id, token, runs_issue, *log_paths))

    def report():
        took = time.time() - started
        after_pct = profile_quota(fetch_usage(), cand, None)[0]
        rules = changed_ids(before[0], rule_snapshot()) if before else []
        if rules and info["outcome"] == "ok":
            info["outcome"] = "rule records changed: " + ", ".join(map(str, rules))
        say(f"outcome: {info['outcome']}")
        quota = (pct_text(d["pct"]), pct_text(after_pct))
        dibs("todo:agent:comment", runs_issue, "--body",
             report_text(run_id, p, cand, started, took, info, quota, rules, log_paths),
             "--idempotency-key", f"curator:report:{run_id}")

    forced = attempt(info, launch)
    forced = attempt(info, report) or forced
    forced = attempt(info, lambda: dibs("todo:agent:release", runs_issue, "--pid", os.getpid(), "--token", token,
                                        "--left", f"Curator run {run_id} finished: {info['outcome']}")) or forced
    outcome = info["outcome"]
    ok_at = int(time.time()) if outcome == "ok" else last.get("ok_at")
    write_last(cfg, p, outcome, ok_at)
    prune_runs(cfg)
    if forced:
        return forced
    return 0 if outcome == "ok" or outcome.startswith("parked at quota") else 3


def attempt(info, step):
    """Run one step after the claim. A stop sets the outcome; Dibs and unexpected errors return exit code 2."""
    try:
        step()
    except StopRun:
        info["outcome"] = "stopped by signal"
        return 3
    except DibsError as e:
        say(f"dibs error after claim: {e}")
        return 2
    except Exception as e:
        traceback.print_exc()
        info["outcome"] = f"curator error: {type(e).__name__}"
        return 2
    return None


def stop_on_signal():
    def handler(signum, _frame):
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        raise StopRun()
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)


def command_run(cfg, p, dry_run):
    run_id = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-") + p["name"]
    d = decide(cfg, p, probe_lock if dry_run else take_lock)
    try:
        if not d["run"]:
            say(f"skip: {d['reason']}" if d["kind"] == "skip" else d["reason"])
            if d["kind"] in ("nothing", "parked") and not dry_run:
                ok_at = int(time.time()) if d["kind"] == "nothing" else read_last(cfg, p).get("ok_at")
                write_last(cfg, p, d["reason"].split(" (")[0], ok_at)
            return 0
        say(d["reason"])
        if dry_run:
            issues = standing_issues(cfg, create=False)
            shown = [i if i is not None else "(created on the first real run)" for i in issues]
            prompt = build_prompt(cfg, p, d["candidate"], run_id, shown[0], shown[1], read_last(cfg, p))
            say(json.dumps(d["candidate"]))
            say(shlex.join(agent_command(p, d["candidate"], "<session-id>")))
            say("--- prompt ---\n" + prompt)
            return 0
        stop_on_signal()
        return do_run(cfg, p, d, run_id)
    finally:
        release_lock(d)


def command_gate(cfg, p, as_json):
    d = decide(cfg, p, probe_lock)
    if as_json:
        say(json.dumps({"run": d["run"], "reason": d["reason"], "candidate": d["candidate"]}))
    else:
        say(d["reason"] if d["run"] else f"skip: {d['reason']}")
    return 0 if d["run"] else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="Unattended Dibs curator")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="gate, then run one pass")
    run.add_argument("--pass", dest="name", required=True)
    run.add_argument("--dry-run", action="store_true")
    gate = sub.add_parser("gate", help="print the gate decision (read-only)")
    gate.add_argument("--pass", dest="name", required=True)
    gate.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        cfg = load_config()
        p = load_pass(cfg, args.name)
        if args.command == "gate":
            return command_gate(cfg, p, args.json)
        return command_run(cfg, p, args.dry_run)
    except ConfigError as e:
        print(f"configuration error: {e}", file=sys.stderr)
        return 2
    except DibsError as e:
        print(f"dibs error: {e}", file=sys.stderr)
        return 2
    except StopRun:
        print("stopped by signal", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
