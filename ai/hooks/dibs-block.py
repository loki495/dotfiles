#!/usr/bin/env python3
"""Dibs bookkeeping without tool calls.

  dibs-block.py stop       Stop (called from stop-gate.sh): apply the ```dibs block(s) in the final message.
  dibs-block.py prompt     UserPromptSubmit: claim tasks named as `dibs <id>`, report the last block's results.
  dibs-block.py heartbeat  PreToolUse: renew the claims this session made, at most every DIBS_BLOCK_BEAT_SECONDS.
  dibs-block.py guard      PreToolUse: process work lines and require a claim for changes; after two denials,
                           create a temporary fallback task. Subagents and Dibs outages pass through.
  dibs-block.py checkpoint PreCompact/SessionEnd: renew leases and refresh the breadcrumb; never releases or completes.
  dibs-block.py recover    SessionStart: list dropped task ids under the working directory, and the breadcrumbs of dead
                           sessions that never got a task.

Block lines (indented lines continue the previous one):
  claim <id>
  note <id>: <text>                the session's one checkpoint comment on the task (added, then edited)
  append <id> ## <Section>         text on the following indented lines goes under that heading
  done <id> sha=<sha|"none: why"> [tests="<cmd>"|tests="none: why"] [docs=a.md,b.md|docs="none: why"] :: <summary>
  atlas <subsystem>: <change>      queued in DIBS_ATLAS_HINTS for the atlas refresh job

Every action is validated and applied once (re-sent blocks are skipped); refusals block the stop once so they
can be fixed, and everything is reported on the next prompt. DIBS_BLOCK_DRY_RUN=1 reports without writing.
"""
import contextlib
import fcntl
import hashlib
import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

CLI = shlex.split(os.environ.get('DIBS_CLI', 'docker exec -u www-data dibs-app php artisan'))
DRY = os.environ.get('DIBS_BLOCK_DRY_RUN') == '1'
STATE_DIR = Path(os.environ.get('DIBS_BLOCK_STATE_DIR')
                 or Path(os.environ.get('XDG_RUNTIME_DIR') or Path.home() / '.cache') / 'dibs-block')
HINTS = Path(os.environ.get('DIBS_ATLAS_HINTS') or Path.home() / '.local/state/dibs-atlas-hints.jsonl')
BEAT_EVERY = int(os.environ.get('DIBS_BLOCK_BEAT_SECONDS', '900'))
BLOCK_RE = re.compile(r'^```dibs[ \t]*\n(.*?)^```[ \t]*$', re.M | re.S)
PROMPT_RE = re.compile(r'(?<![/\w#])dibs[ \t]+#?(\d+)\b', re.I)
SHA_RE = re.compile(r'^[0-9a-f]{7,40}$')
LEASE = '90'
MUTATING = {'Edit', 'Write', 'MultiEdit', 'NotebookEdit', 'Bash'}
FILE_CMDS = {'rm', 'mv', 'cp', 'touch', 'mkdir', 'rmdir', 'ln', 'tee', 'chmod', 'chown', 'truncate', 'install'}
GIT_MUT = {'commit', 'push', 'merge', 'reset', 'rebase', 'checkout', 'switch', 'add', 'rm', 'mv', 'clean', 'stash',
           'cherry-pick', 'pull', 'tag', 'apply', 'restore', 'revert', 'am', 'init', 'clone'}
COMPOSE_MUT = {'up', 'down', 'start', 'stop', 'restart', 'rm', 'build', 'run', 'create', 'kill'}
PKG_CMDS = {'npm', 'pnpm', 'yarn', 'pip', 'pip3', 'composer'}
PKG_MUT = {'install', 'i', 'add', 'remove', 'uninstall', 'update', 'require'}
WRAPPERS = {'sudo', 'env', 'command', 'nohup', 'time', 'nice'}


class Refused(Exception):
    pass


class WorkRefused(Refused):
    pass


def cli(cmd, *args):
    p = subprocess.run(CLI + [f'todo:agent:{cmd}', *args], capture_output=True, text=True, timeout=20)
    if p.returncode != 0:
        raise Refused((p.stdout.strip() or p.stderr.strip() or f'{cmd} failed')[-300:])
    return json.loads(p.stdout) if p.stdout.strip() else {}


def agent_pid():
    if os.environ.get('DIBS_AGENT_PID'):
        return os.environ['DIBS_AGENT_PID']
    pid = os.getppid()
    for _ in range(8):
        try:
            if Path(f'/proc/{pid}/comm').read_text().strip() == 'claude':
                return str(pid)
            pid = int(Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            break
        if pid <= 1:
            break
    return str(os.getppid())


class Session:
    def __init__(self, data):
        self.id = data.get('session_id') or ''
        self.cwd = data.get('cwd') or os.getcwd()
        self.path = STATE_DIR / (re.sub(r'[^A-Za-z0-9_-]', '_', self.id) + '.json')
        try:
            self.state = json.loads(self.path.read_text())
        except (OSError, ValueError):
            self.state = {}
        self.state.setdefault('claims', {})
        self.state.setdefault('applied', [])
        self.state.setdefault('report', [])
        self.state.setdefault('crumbs', {})
        self.warns = []

    def save(self):
        old = os.umask(0o077)
        try:
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix('.tmp')
            tmp.write_text(json.dumps(self.state))
            os.replace(tmp, self.path)
        finally:
            os.umask(old)

    @property
    def agent(self):
        return f"claude:{os.environ.get('SESSIONEER_SELF') or 'claude'}:{self.id}"

    def held(self):
        return {str(c['issueId']) for c in cli('claims', f'--held-by={self.id}')}

    def git(self, *args):
        return subprocess.run(['git', '-C', self.cwd, *args], capture_output=True, text=True, timeout=10)

    # actions -------------------------------------------------------------
    def claim(self, issue):
        if issue in self.state['claims']:
            return f'claim {issue}: already held by this session'
        if cli('show', issue).get('state') != 'OPEN':
            raise Refused(f'task {issue} is not open')
        if DRY:
            return f'claim {issue}: would claim (dry run)'
        r = cli('claim', issue, f'--agent={self.agent}', f'--pid={agent_pid()}', f'--minutes={LEASE}', f'--path={self.cwd}')
        self.state['claims'][issue] = r['capability_token']
        return f'claimed {issue} (capability token {r["capability_token"]}, for MCP calls on this claim)'

    def require_held(self, issue):
        if issue not in self.state['claims'] and issue not in self.held():
            raise Refused(f'task {issue} is not claimed by this session (claim it first)')

    def note(self, issue, text):
        self.require_held(issue)
        if not text.strip():
            raise Refused('empty note')
        if DRY:
            return f'note {issue}: would update the checkpoint (dry run)'
        return self.put(issue, text.strip(), f'dibs-block:{self.key}')

    def crumb(self, issue, progress):
        a = self.state['crumbs'][issue]
        try:
            branch = self.git('branch', '--show-current').stdout.strip()
            status = [x[:200] for x in self.git('status', '--short').stdout.splitlines()[:20]]
        except (OSError, subprocess.TimeoutExpired):
            branch, status = '', []
        return '\n'.join([
            'Auto checkpoint, refreshed by the dibs-block hook.',
            f'Goal: {a["goal"]}', f'Session: {self.id}', f'Workdir: {self.cwd}', f'Branch: {branch or "unknown"}',
            f'Updated: {datetime.now(timezone.utc).isoformat(timespec="seconds")}',
            'Git status (bounded):', *(status or ['(clean or unavailable)']),
            *([f'Latest prompt: {self.state["intent"]}'] if self.state.get('intent') not in (None, a['goal']) else []),
            f'Progress: {progress or "none recorded yet"}',
            'Next step: review this task, place it under the correct project or parent, then continue the goal.'])

    def put(self, issue, progress, key):
        notes = self.state.setdefault('notes', {})
        prev = notes.get(issue)
        text = self.crumb(issue, progress) if issue in self.state['crumbs'] else progress
        if prev:
            r = cli('comment', f'--comment-id={prev["id"]}', f'--expected-revision={prev["revision"]}', f'--body={text}')
            if not r.get('conflict'):
                notes[issue] = {'id': prev['id'], 'revision': r.get('revision', prev['revision'] + 1), 'text': progress}
                return f'note {issue}: checkpoint comment {prev["id"]} updated'
        r = cli('comment', issue, f'--body={text}', f'--idempotency-key={key}')
        notes[issue] = {'id': r['comment_id'], 'revision': r.get('revision', 1), 'text': progress}
        return f'note {issue}: checkpoint comment {r["comment_id"]} added'

    def beat(self, refresh=True, only=None):
        for issue, token in list(self.state['claims'].items()):
            if only is not None and issue not in only:
                continue
            try:
                cli('heartbeat', issue, f'--pid={agent_pid()}', f'--token={token}', f'--minutes={LEASE}')
            except Refused:
                self.state['claims'].pop(issue)
            except (OSError, subprocess.TimeoutExpired) as e:
                self.warns.append(f'lease renewal for {issue} failed ({type(e).__name__})')
        if not refresh:
            return
        try:
            held = self.held()
            self.ensure(held)
            for issue, c in self.state['crumbs'].items():
                if issue in held:
                    self.put(issue, self.state.get('notes', {}).get(issue, {}).get('text', ''), f'dibs-crumb:{c["key"]}')
        except (Refused, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as e:
            self.warns.append(f'breadcrumb refresh failed ({type(e).__name__}: {str(e)[:100]}); Dibs may be offline')

    def ensure(self, held):
        a = self.state.get('auto') or {}
        for issue in sorted(held - set(self.state['crumbs'])):
            if issue == a.get('id'):
                goal, key = a['goal'], a['key']
            else:
                goal = self.state.get('intent') or '(no prompt recorded)'
                key = hashlib.sha256(f'{self.id}\next\n{issue}'.encode()).hexdigest()[:24]
            try:
                self.register(issue, goal, key)
            except (Refused, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as e:
                self.state['crumbs'].pop(issue, None)
                self.warns.append(f'breadcrumb for held task {issue} failed ({type(e).__name__}: {str(e)[:100]})')

    def register(self, issue, goal, key):
        self.state['crumbs'][issue] = {'goal': goal, 'key': key}
        self.save()
        self.put(issue, '', f'dibs-crumb:{key}')
        self.save()

    def track(self):
        held = self.held()
        if held:
            self.ensure(held)
            return None
        a = self.state.get('auto')
        alive = False
        if a:
            try:
                alive = cli('show', a['id']).get('state') == 'OPEN'
            except Refused:
                # a failing show is a deleted task only if the CLI still answers another call; an outage raises here
                self.held()
                self.state['crumbs'].pop(a['id'], None)
                self.state.get('notes', {}).pop(a['id'], None)
        if alive:
            issue = a['id']
            self.state['claims'].pop(issue, None)
        else:
            p = self.state.get('pending_create')
            if not p:
                goal = self.state.get('intent') or '(no prompt recorded)'
                seq = a['seq'] + 1 if a else 0
                key = hashlib.sha256(f'{self.id}\nauto\n{seq}\n{goal}'.encode()).hexdigest()[:24]
                p = self.state['pending_create'] = {'seq': seq, 'goal': goal, 'key': key, 'cwd': self.cwd}
                self.save()
            extra = [f'--{k}={v}' for k in ('area', 'parent', 'group') if (v := os.environ.get(f'DIBS_TRACK_{k.upper()}'))]
            r = cli('create', f'Auto-tracked: {p["goal"][:80]}', '--temporary', *extra, f'--idempotency-key=dibs-track:{p["key"]}',
                    f'--body=Goal: {p["goal"]}\nWorkdir: {p["cwd"]}\nTemporary task opened by the dibs-block guard before the first '
                    'persistent change. Place it under the correct project or parent, or close it if it is not real work.')
            issue = str(r['id'])
            self.state['auto'] = {'id': issue, 'seq': p['seq'], 'goal': p['goal'], 'key': p['key']}
            self.state.pop('pending_create')
            self.state.pop('intent', None)
            self.save()
        self.claim(issue)
        self.save()
        a = self.state['auto']
        self.register(issue, a['goal'], a['key'])
        place = '' if os.environ.get('DIBS_TRACK_PARENT') or os.environ.get('DIBS_TRACK_AREA') else (
            ' Automatic creation could not infer the project: place it under the correct project or parent before continuing.')
        token = self.state['claims'][issue]
        return (f'Dibs task {issue} was opened and claimed for this session because a persistent change started without a claim; '
                f'a breadcrumb is recorded.{place} Review it with todo_show {issue}. '
                f'Capability token for MCP calls on this claim (todo_complete, todo_release, todo_comment): {token}')

    def append(self, issue, section, text):
        self.require_held(issue)
        if not text.strip():
            raise Refused('nothing to append')
        for _ in range(2):
            cur = cli('show', issue)
            body = append_to_section(cur.get('body') or '', section, text.strip())
            if DRY:
                return f'append {issue}: would add under "## {section}" (dry run)'
            try:
                if not cli('update', issue, f'--expected-revision={cur["revision"]}', f'--body={body}').get('conflict'):
                    return f'append {issue}: added under "## {section}"'
            except Refused as e:
                if 'conflict' not in str(e).lower():
                    raise
        raise Refused(f'task {issue} kept changing; append not applied')

    def done(self, issue, args, summary):
        self.require_held(issue)
        token = self.state['claims'].get(issue)
        if not token:
            raise Refused(f'task {issue} was claimed outside the block; close it with todo_complete')
        if not summary.strip():
            raise Refused('done needs a summary after "::"')
        sha = args.get('sha', '')
        result = {'done_when_held': True}
        if SHA_RE.match(sha):
            if self.git('cat-file', '-e', f'{sha}^{{commit}}').returncode != 0:
                raise Refused(f'commit {sha} does not exist in {self.cwd}')
            if self.git('merge-base', '--is-ancestor', sha, 'HEAD').returncode != 0:
                raise Refused(f'commit {sha} is not on the current branch')
            result['commit'] = sha
        elif sha.startswith('none:') and len(sha) > 6:
            result['commit'] = sha
        else:
            raise Refused('done needs sha=<commit> or sha="none: <reason>"')
        if 'tests' in args:
            t = args['tests']
            result['tests'] = t if t.startswith('none:') else {'command': t, 'exit_code': 0}
        if 'docs' in args:
            d = args['docs']
            result['docs'] = d if d.startswith('none:') else [x for x in d.split(',') if x]
        if DRY:
            return f'done {issue}: would complete (dry run)'
        cli('complete', issue, f'--pid={agent_pid()}', f'--token={token}', f'--summary={summary.strip()}',
            f'--result={json.dumps(result)}')
        self.state['claims'].pop(issue, None)
        return f'done {issue}: completed'

    def atlas(self, subsystem, text):
        if not subsystem or not text.strip():
            raise Refused('atlas needs "<subsystem>: <change>"')
        root = self.git('rev-parse', '--show-toplevel').stdout.strip() or self.cwd
        head = self.git('rev-parse', 'HEAD').stdout.strip()
        if DRY:
            return f'atlas {subsystem}: would queue hint (dry run)'
        HINTS.parent.mkdir(parents=True, exist_ok=True)
        with HINTS.open('a') as f:
            f.write(json.dumps({'ts': int(time.time()), 'session': self.id, 'repo': root, 'head': head,
                                'subsystem': subsystem, 'change': text.strip()}) + '\n')
        if os.environ.get('DIBS_ATLAS_SYNC') != 'off':
            subprocess.Popen([sys.executable, str(Path(__file__).resolve().parents[1] / 'scripts' / 'atlas-refresh.py'), 'sync-hints'],
                             start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f'atlas {subsystem}: hint queued'

    def run(self, action):
        self.key = hashlib.sha256(f'{self.id}\n{action}'.encode()).hexdigest()[:24]
        if self.key in self.state['applied']:
            return None, None
        try:
            msg = dispatch(self, action)
        except Refused as e:
            return None, f'refused "{action.splitlines()[0][:80]}": {e}'
        except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as e:
            return None, f'failed "{action.splitlines()[0][:80]}": {type(e).__name__}: {e}'
        if not DRY:
            self.state['applied'] = (self.state['applied'] + [self.key])[-500:]
        return msg, None


def append_to_section(body, section, text):
    lines = body.split('\n')
    head = f'## {section}'.strip()
    for i, line in enumerate(lines):
        if line.strip() == head:
            end = next((j for j in range(i + 1, len(lines)) if re.match(r'#{1,2} ', lines[j])), len(lines))
            while end > i + 1 and not lines[end - 1].strip():
                end -= 1
            return '\n'.join(lines[:end] + [text] + lines[end:]).rstrip('\n')
    return (body.rstrip('\n') + f'\n\n{head}\n{text}').lstrip('\n')


def fence_step(line, fence):
    """Track CommonMark-style backtick and tilde fences, including their length."""
    if fence:
        char, size = fence
        if re.fullmatch(r' {0,3}' + re.escape(char) + '{' + str(size) + r',}[ \t]*', line):
            return None
        return fence
    m = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line)
    if m and (m[1][0] != '`' or '`' not in m[2]):
        return (m[1][0], len(m[1]))
    return None


def actions(message):
    out, fence, dibs = [], None, False
    for line in (message or '').splitlines():
        old = fence
        fence = fence_step(line, fence)
        if old is None and fence is not None:
            dibs = bool(re.fullmatch(r' {0,3}`{3,}dibs[ \t]*', line))
            continue
        if old is not None and fence is None:
            dibs = False
            continue
        if dibs:
            if line.startswith((' ', '\t')) and out:
                out[-1] += '\n' + line.strip()
            elif line.strip():
                out.append(line.strip())
        elif fence is None:
            m = re.fullmatch(r'\[complete (\d+) \| (.*?) \| (.*)\]\s*', line)
            if m:
                out.append(f'done {m[1]} {m[2]} :: {m[3]}')
    return out


def dispatch(s, action):
    first, _, rest = action.partition('\n')
    m = re.match(r'(claim|note|append|done|atlas)\b\s*(.*)$', first)
    if not m:
        raise Refused('unknown action (use claim, note, append, done or atlas)')
    verb, tail = m.groups()
    if verb == 'atlas':
        sub, _, text = tail.partition(':')
        return s.atlas(sub.strip(), (text + '\n' + rest).strip())
    im = re.match(r'#?(\d+)\b\s*(.*)$', tail)
    if not im:
        raise Refused(f'{verb} needs a task id')
    issue, tail = im.groups()
    if verb == 'claim':
        return s.claim(issue)
    if verb == 'note':
        return s.note(issue, (tail.lstrip(':').strip() + '\n' + rest).strip())
    if verb == 'append':
        sm = re.match(r'##\s+(.+)$', tail)
        if not sm:
            raise Refused('append needs "## <Section>"')
        return s.append(issue, sm.group(1).strip(), rest)
    head, sep, summary = tail.partition('::')
    if not sep:
        raise Refused('done needs ":: <summary>"')
    try:
        args = dict(kv.split('=', 1) for kv in shlex.split(head) if '=' in kv)
    except ValueError as e:
        raise Refused(f'unreadable arguments: {e}')
    return s.done(issue, args, (summary + '\n' + rest).strip())


def scratch(path):
    """True for targets that are not project state: /dev/null, /tmp and the runtime dir."""
    roots = ['/tmp'] + ([os.environ['XDG_RUNTIME_DIR'].rstrip('/')] if os.environ.get('XDG_RUNTIME_DIR') else [])
    return path == '/dev/null' or path.startswith('$XDG_RUNTIME_DIR') or any(path == r or path.startswith(r + '/') for r in roots)


def segment_mutates(t):
    while t and (t[0] in WRAPPERS or re.match(r'\w+=', t[0])):
        t = t[1:]
    if not t:
        return False
    c, args = os.path.basename(t[0]), t[1:]
    paths = [a for a in args if not a.startswith('-')]
    if c in FILE_CMDS:
        return not all(scratch(a) for a in paths)
    if c == 'sed':
        return any(a == '--in-place' or a.startswith('--in-place=') or re.match(r'-[a-zA-Z]*i', a) for a in args)
    if c == 'git':
        rest, i = [], 0
        while i < len(args):
            if args[i] in ('-C', '-c'):
                i += 1
            elif not args[i].startswith('-'):
                rest.append(args[i])
            i += 1
        sub = rest[0] if rest else ''
        if sub == 'branch':
            return bool(set(args[args.index('branch') + 1:]) - {'-a', '-r', '-v', '--show-current', '--list'}) if 'branch' in args else False
        if sub == 'worktree':
            return rest[1:2] != ['list']
        return sub in GIT_MUT
    if c in ('docker', 'docker-compose'):
        return bool(COMPOSE_MUT & set(paths)) and (c == 'docker-compose' or 'compose' in paths)
    if c in PKG_CMDS:
        return bool(PKG_MUT & set(paths))
    if c == 'curl':
        for i, a in enumerate(args):
            if a in ('-d', '-F', '-T') or a.startswith(('--data', '--form', '--upload-file')):
                return True
            if a == '-X' and i + 1 < len(args) and args[i + 1].upper() in ('POST', 'PUT', 'DELETE', 'PATCH'):
                return True
            if re.match(r'-X(POST|PUT|DELETE|PATCH)$', a, re.I):
                return True
    return False


def bash_mutates(cmd):
    """Denylist of real mutations, tested on the command with quoted strings removed."""
    s = re.sub(r"\"[^\"]*\"|'[^']*'", 'Q', cmd)
    for m in re.finditer(r'(?:\d*|&)>>?\s*(\S+)', s):
        if not m.group(1).startswith('&') and not scratch(m.group(1)):
            return True
    s = re.sub(r'(?:\d*|&)>>?\s*\S+', ' ', s)
    return any(segment_mutates(seg.split()) for seg in re.split(r'&&|\|\||[;|\n()`{}]', s))


@contextlib.contextmanager
def locked(sid):
    old = os.umask(0o077)
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        f = open(STATE_DIR / (re.sub(r'[^A-Za-z0-9_-]', '_', sid) + '.lock'), 'a')
    finally:
        os.umask(old)
    with f:
        fcntl.flock(f, fcntl.LOCK_EX)
        yield


def warn(s):
    if s.warns:
        print(json.dumps({'systemMessage': 'Dibs tracking: ' + '; '.join(s.warns)}))


def emit(event, **fields):
    print(json.dumps({'hookSpecificOutput': {'hookEventName': event, **fields}}))


def transcript_lines(data, wait):
    path, tid = data.get('transcript_path'), data.get('tool_use_id')
    if not path:
        return []
    deadline = time.monotonic() + (min(max(float(os.environ.get('DIBS_WORK_WAIT_SECONDS', '1.5')), 0), 1.5) if wait else 0)
    while True:
        try:
            rows = Path(path).read_text().splitlines()
        except OSError:
            return []
        entries = []
        found = False
        for row in rows:
            try:
                obj = json.loads(row)
                if not isinstance(obj, dict) or obj.get('type') != 'assistant':
                    continue
                content = obj.get('message', {}).get('content', [])
                if not isinstance(content, list):
                    continue
                found |= any(isinstance(c, dict) and c.get('type') == 'tool_use' and c.get('id') == tid and tid for c in content)
                entries.extend(c.get('text', '') for c in content if isinstance(c, dict) and c.get('type') == 'text')
            except (ValueError, AttributeError, TypeError):
                continue
        if found or time.monotonic() >= deadline:
            return entries
        time.sleep(min(0.05, max(0, deadline - time.monotonic())))


def work_lines(entries):
    fence, result, index = None, [], 0
    for entry in entries:
        for line in entry.splitlines():
            index += 1
            old = fence
            fence = fence_step(line, fence)
            if old is not None or fence is not None:
                continue
            m = re.fullmatch(r'\[work (\d+|new) \| (.+) \| ([a-z-]+(?:\+[a-z-]+)*)\]\s*', line)
            if m and all(t in RULES.TYPE_KEYS for t in m[3].split('+')):
                result.append((index, *m.groups()))
    return result


spec = importlib.util.spec_from_file_location('rule_inject', Path(__file__).with_name('rule-inject.py'))
RULES = importlib.util.module_from_spec(spec)
spec.loader.exec_module(RULES)


def process_work_claim(s, held, index, issue, description, types):
    if issue == 'new':
        key = hashlib.sha256(f'{s.id}\nwork\n{index}'.encode()).hexdigest()[:24]
        r = cli('create', description, '--temporary', f'--idempotency-key=dibs-work:{key}',
                f'--body=Goal: {description}\nWorkdir: {s.cwd}\nType: {types}')
        issue = str(r['id'])
    if issue not in held:
        s.state['claims'].pop(issue, None)
        try:
            s.claim(issue)
        except Refused as e:
            raise WorkRefused(str(e)) from e
        held.add(issue)
        key = hashlib.sha256(f'{s.id}\nwork\n{index}'.encode()).hexdigest()[:24]
        s.register(issue, description, key)
    return issue


def guard(data):
    tool, inp = data.get('tool_name'), data.get('tool_input') or {}
    if DRY or data.get('agent_id'):
        return
    mutation = tool in MUTATING and (bash_mutates(inp.get('command') or '') if tool == 'Bash' else
                                     not scratch(str(inp.get('file_path') or inp.get('notebook_path') or '')))
    if not data.get('session_id'):
        if mutation:
            print(json.dumps({'systemMessage': 'Dibs tracking: no session id; change goes ahead untracked'}))
        return
    try:
        with locked(data['session_id']):
            s = Session(data)
            # Check live claims before waiting; an externally held claim is not in local state.
            # Record the breadcrumb before contacting Dibs for a mutating call.
            held_before = None
            if mutation:
                s.state.setdefault('breadcrumb', {'prompt': s.state.get('intent') or '(no prompt recorded)', 'cwd': s.cwd,
                    'branch': s.git('branch', '--show-current').stdout.strip(), 'ts': int(time.time()), 'pid': int(agent_pid())})
                s.save()
                held_before = s.held()
            entries = transcript_lines(data, not bool(held_before) if mutation else not bool(s.state['claims']))
            lines = [x for x in work_lines(entries) if x[0] > s.state.get('work_index', 0)]
            if not mutation and not lines:
                return
            if mutation or lines:
                s.state.setdefault('breadcrumb', {'prompt': s.state.get('intent') or '(no prompt recorded)', 'cwd': s.cwd,
                    'branch': s.git('branch', '--show-current').stdout.strip(), 'ts': int(time.time()), 'pid': int(agent_pid())})
                s.save()
            try:
                held = held_before if held_before is not None else s.held()
                notices, rule_texts, hold = [], [], False
                for index, issue, description, types in lines:
                    try:
                        issue = process_work_claim(s, held, index, issue, description, types)
                    except WorkRefused as e:
                        # A healthy claims response distinguishes a semantic refusal from an outage.
                        s.held()
                        s.state['work_index'] = index
                        s.save()
                        s.warns.append(f'work line refused: {e}')
                        continue
                    token = s.state['claims'].get(issue)
                    notices.append(f'Dibs task {issue} claimed for this session.' +
                                   (f' Capability token for MCP calls on this claim (todo_complete, todo_release, todo_comment): {token}' if token else ''))
                    rules = RULES.rules_for_types(types.split('+'), s.id, data.get('agent_id'), data.get('tool_use_id'))
                    if rules:
                        rule_texts.extend(rules)
                        if mutation and issue not in s.state.setdefault('work_held', []):
                            s.state['work_held'].append(issue)
                            hold = True
                    s.state['work_index'] = index
                    s.state['denials'] = 0
                    s.save()
                if held:
                    s.state['denials'] = 0
                if hold:
                    s.save()
                    emit('PreToolUse', permissionDecision='deny', permissionDecisionReason='\n\n'.join(notices + rule_texts) + '\nPlease retry the call.')
                    return
                if notices:
                    context = '\n\n'.join(notices + rule_texts +
                                          (['; '.join(s.warns)] if s.warns else []) +
                                          ([RULES.LATE] if rule_texts else []))
                    s.save()
                    emit('PreToolUse', permissionDecision='allow', additionalContext=context)
                    return
                if held:
                    if s.warns:
                        warn(s)
                    s.state.pop('breadcrumb', None)
                    s.save()
                    return
                if not mutation and s.warns:
                    warn(s)
                if mutation:
                    if s.state.get('denials', 0) < 2:
                        s.state['denials'] = s.state.get('denials', 0) + 1
                        s.save()
                        ids = re.findall(r'(?i)(?:\b(?:dibs|task|plan)\s+#?|#)(\d+)', s.state.get('intent', ''))
                        reason = 'Output [work <id or new> | <description> | <type>] on its own line outside code fences before related work. Types: ' + ', '.join(RULES.TYPE_KEYS)
                        if ids:
                            reason += '. Candidates: ' + ', '.join('task ' + i for i in ids)
                        emit('PreToolUse', permissionDecision='deny', permissionDecisionReason=reason)
                        return
                    note = s.track()
                    s.state['denials'] = 0
                    s.save()
                    print(json.dumps({'systemMessage': 'Dibs tracking: fallback task opened after two denials.', 'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'allow', 'additionalContext': note}}))
            except (Refused, OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as e:
                s.state['pending'] = {'goal': s.state.get('intent'), 'cwd': s.cwd, 'ts': int(time.time())}
                s.save()
                print(json.dumps({'systemMessage': f'Dibs tracking failed ({type(e).__name__}: {str(e)[:200]}); the change goes ahead and the intent is kept locally'}))
    except Exception as e:
        print(json.dumps({'systemMessage': f'Dibs tracking state failed ({type(e).__name__}: {str(e)[:200]}); the change goes ahead untracked'}))


def unrecorded():
    """Breadcrumbs of dead sessions that never got a task."""
    out = []
    for f in sorted(STATE_DIR.glob('*.json')):
        try:
            st = json.loads(f.read_text())
            b = st.get('breadcrumb')
            if b and not st.get('auto') and not st.get('claims') and not Path(f'/proc/{int(b["pid"])}').exists():
                out.append(f'session {f.stem}: {b["cwd"]} on {b.get("branch") or "unknown branch"}, prompt: {b["prompt"][:200]}')
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            continue
    return out


def recover(data):
    cwd = data.get('cwd') or os.getcwd()
    parts = []
    try:
        r = cli('dropped', f'--path={cwd}')
        items = r if isinstance(r, list) else (r.get('issues') or r.get('items') or [])
        ids = []
        for i in items:
            v = i.get('issueId', i.get('id')) if isinstance(i, dict) else i
            if isinstance(v, int) and not isinstance(v, bool) or isinstance(v, str) and v.isdigit():
                ids.append(str(v))
        if ids:
            parts.append('Dropped Dibs tasks under this directory: ' + ', '.join(ids[:20])
                         + '. Inspect each with todo_show before resuming; nothing is claimed or run automatically.')
    except (Refused, OSError, ValueError, AttributeError, subprocess.TimeoutExpired):
        parts.append('Dibs recovery unavailable (offline or failed): dropped tasks were not checked.')
    lost = unrecorded()
    if lost:
        parts.append('Changes made by dead sessions with no Dibs task (file one if the work matters): ' + ' | '.join(lost[:10]))
    if parts:
        emit('SessionStart', additionalContext=' '.join(parts))


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ''
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    if mode == 'guard':
        return guard(data)
    if mode == 'recover':
        return recover(data)
    if not data.get('session_id'):
        return
    quiet = mode in ('heartbeat', 'checkpoint') or (mode == 'stop' and not actions(data.get('last_assistant_message')))
    if quiet and not (STATE_DIR / (re.sub(r'[^A-Za-z0-9_-]', '_', data['session_id']) + '.json')).exists():
        return
    with locked(data['session_id']):
        run_mode(mode, data)


def run_mode(mode, data):
    if mode == 'heartbeat':
        path = STATE_DIR / (re.sub(r'[^A-Za-z0-9_-]', '_', data['session_id']) + '.json')
        if not path.exists():
            return
        s = Session(data)
        if time.time() - s.state.get('beat', 0) < BEAT_EVERY:
            return
        s.state['beat'] = time.time()
        s.beat()
        s.save()
        return warn(s)
    if mode == 'checkpoint':
        s = Session(data)
        s.beat()
        s.save()
        return warn(s)
    if mode == 'prompt':
        ids = list(dict.fromkeys(PROMPT_RE.findall(data.get('prompt') or '')))
        s = Session(data)
        goal = ' '.join((data.get('prompt') or '').split())[:500]
        fresh = bool(goal) and s.state.get('intent') != goal
        if fresh:
            s.state['intent'] = goal
        if not ids and not s.state['report']:
            if fresh:
                s.save()
            return
        lines = s.state['report']
        s.state['report'] = []
        for issue in ids:
            ok, err = s.run(f'claim {issue}')
            lines += [x for x in (ok, err) if x]
        s.save()
        if lines:
            print(json.dumps({'hookSpecificOutput': {'hookEventName': 'UserPromptSubmit', 'additionalContext':
                              'Dibs block results:\n- ' + '\n- '.join(lines)}}))
        return
    if mode == 'stop':
        todo = actions(data.get('last_assistant_message'))
        if not todo:
            s = Session(data)
            s.beat()
            s.save()
            warn(s)
            return
        s, done, refused = Session(data), [], []
        # Newly claimed tasks already have a fresh lease; renew claims held before bookkeeping.
        previously_claimed = set(s.state['claims'])
        for a in todo:
            ok, err = s.run(a)
            done += [ok] if ok else []
            refused += [err] if err else []
        s.state['report'] += done + refused
        s.beat(refresh=False, only=previously_claimed)
        s.save()
        if refused and not data.get('stop_hook_active'):
            print(json.dumps({'decision': 'block', 'reason': 'Dibs block: ' + '; '.join(refused)
                              + '. Fix the block (or use the MCP tools) and resend; applied lines are not repeated.'}))
        elif done or refused:
            print(json.dumps({'systemMessage': 'Dibs: ' + '; '.join(done + refused)}))


if __name__ == '__main__':
    main()
