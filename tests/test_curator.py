"""ai/scripts/curator.py as a subprocess, against fake sessioneer, Dibs CLI and claude.

Every external command is an executable script in a temp dir, selected only through the
environment overrides the Contract defines. Each fake records its argv (and stdin for claude)
to a JSON-lines file so the tests can pin call shapes. Nothing real is ever called.
"""
import datetime
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'ai' / 'scripts' / 'curator.py'

MODEL = 'claude-sonnet-5-5'
NOTE_LINE = 'Note: process liveness could not be verified in this environment (weaker-assurance claim).'
WRITE_CMDS = {'todo:agent:create', 'todo:agent:claim', 'todo:agent:heartbeat',
              'todo:agent:comment', 'todo:agent:release'}
RUNS_ID, PROPOSALS_ID = 20, 21
TOKEN = f'tok-{RUNS_ID}'

FAKE_SESSIONEER = '''#!__PY__
import json, os, sys
d = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(d, 'sessioneer.jsonl'), 'a') as f:
    f.write(json.dumps(sys.argv[1:]) + '\\n')


def emit(name):
    rc_path = os.path.join(d, name + '.rc')
    rc = int(open(rc_path).read()) if os.path.exists(rc_path) else 0
    p = os.path.join(d, name + '.json')
    if os.path.exists(p):
        sys.stdout.write(open(p).read())
    sys.exit(rc)


if '--usage' in sys.argv:
    emit('usage')
elif '--list' in sys.argv:
    emit('list')
sys.exit(64)
'''

FAKE_DIBS = '''#!__PY__
import json, os, sys
d = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[1:]
idx = next((k for k, a in enumerate(argv) if a.startswith('todo:agent:')), None)
if idx is None:
    sys.stderr.write('no todo:agent command\\n')
    sys.exit(64)
cmd, rest = argv[idx], argv[idx + 1:]
with open(os.path.join(d, 'dibs.jsonl'), 'a') as f:
    f.write(json.dumps({'argv': argv, 'cmd': cmd, 'args': rest}) + '\\n')
sp = os.path.join(d, 'dibs_state.json')
state = json.load(open(sp))
if cmd in state.get('fail', []):
    sys.stderr.write('dibs failure: ' + cmd + '\\n')
    sys.exit(1)


def out(obj):
    print(json.dumps(obj))
    if state.get('note'):
        print('__NOTE__')
    extra = state.get('trailing', {}).get(cmd)
    if extra:
        print(extra)


def flags(args):
    r = {}
    for k, a in enumerate(args):
        if a.startswith('--') and k + 1 < len(args):
            r[a] = args[k + 1]
    return r


if cmd == 'todo:agent:list':
    out({'tasks': state['tasks']})
elif cmd == 'todo:agent:create':
    n = state.get('next_id', 100)
    state['next_id'] = n + 1
    state['tasks'].append({'id': n, 'title': rest[0], 'state': 'OPEN', 'labels': ['curator'],
                           'modifiedAt': None})
    tmp = sp + '.tmp'
    json.dump(state, open(tmp, 'w'))
    os.replace(tmp, sp)
    out({'id': n, 'title': rest[0]})
elif cmd == 'todo:agent:claim':
    if state.get('claim_refuse'):
        sys.stderr.write('claim refused\\n')
        sys.exit(1)
    out({'capability_token': 'tok-' + rest[0], 'issue': int(rest[0])})
elif cmd in ('todo:agent:heartbeat', 'todo:agent:comment', 'todo:agent:release'):
    out({'ok': True})
else:
    sys.exit(64)
'''.replace('__NOTE__', NOTE_LINE)

FAKE_CLAUDE = '''#!__PY__
import json, os, subprocess, sys, time
d = os.path.dirname(os.path.abspath(__file__))
stdin = sys.stdin.read()
if '--system-prompt' in sys.argv:
    with open(os.path.join(d, 'probe.jsonl'), 'a') as f:
        f.write(json.dumps({'argv': sys.argv[1:], 'stdin': stdin, 'env': dict(os.environ)}) + '\\n')
    if os.path.exists(os.path.join(d, 'vanish_after_probe')):
        os.unlink(os.path.abspath(__file__))
    raw = os.path.join(d, 'probe_scenario.json')
    if os.path.exists(raw):
        sc = json.load(open(raw))
        time.sleep(sc.get('sleep', 0))
        for e in sc.get('events', []):
            print(json.dumps(e), flush=True)
        sys.exit(sc.get('exit', 0))
    profile = 'work' if os.environ.get('CLAUDE_CONFIG_DIR', '').endswith('.claude-work') else 'personal'
    try:
        entry = json.load(open(os.path.join(d, 'usage.json')))['agents']['claude']['profiles'][profile]
        assert entry['ok'] is True
        quota = entry['quota']
        windows = {}
        for key, window in (('session', 'five_hour'), ('week_all', 'seven_day')):
            windows[window] = {'utilization': quota[key]['pct'] / 100}
            if 'resets_at' in quota[key]:
                windows[window]['resetsAt'] = quota[key]['resets_at']
    except Exception:
        sys.exit(1)
    print(json.dumps({'type': 'rate_limit_event', 'rate_limit_info': {'status': 'allowed', 'unifiedWindows': windows}}))
    sys.exit(0)
rec = {'argv': sys.argv[1:], 'stdin': stdin, 'env': dict(os.environ), 'cwd': os.path.realpath(os.getcwd()),
       'listing': sorted(os.listdir('.')), 'pid': os.getpid(), 'pgrp': os.getpgrp(), 'sid': os.getsid(0),
       'parent_pgrp': os.getpgid(os.getppid())}
try:
    rec['lock'] = open('../curator.lock').read()
except OSError:
    rec['lock'] = None
with open(os.path.join(d, 'claude.jsonl'), 'a') as f:
    f.write(json.dumps(rec) + '\\n')
sp = os.path.join(d, 'claude_scenario.json')
sc = json.load(open(sp)) if os.path.exists(sp) else {'steps': []}


def atomic(path, obj):
    tmp = path + '.tmp'
    json.dump(obj, open(tmp, 'w'))
    os.replace(tmp, path)


for st in sc['steps']:
    if 'emit' in st:
        print(json.dumps(st['emit']), flush=True)
    elif 'sleep' in st:
        time.sleep(st['sleep'])
    elif 'rules' in st:
        dp = os.path.join(d, 'dibs_state.json')
        state = json.load(open(dp))
        for i in st['rules'].get('change', []):
            for t in state['tasks']:
                if t['id'] == i:
                    t['modifiedAt'] = 'changed-by-run'
        for i in st['rules'].get('remove', []):
            state['tasks'] = [t for t in state['tasks'] if t['id'] != i]
        for i in st['rules'].get('add', []):
            state['tasks'].append({'id': i, 'title': 'new rule', 'state': 'OPEN', 'labels': ['rule'],
                                   'modifiedAt': 'now'})
        for i in st['rules'].get('touch_other', []):
            for t in state['tasks']:
                if t['id'] == i:
                    t['modifiedAt'] = 'changed-by-run'
        atomic(dp, state)
    elif 'spawn_child' in st:
        p = subprocess.Popen(['sleep', '60'], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        open(os.path.join(d, 'child.pid'), 'w').write(str(p.pid))
    elif 'stderr' in st:
        sys.stderr.write(st['stderr'])
        sys.stderr.flush()
    elif 'mark' in st:
        open(os.path.join(d, st['mark']), 'w').write('1')
sys.exit(sc.get('exit', 0))
'''

FAKE_PRECHECK = '''#!__PY__
import json, os, sys
d = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(d, 'pre.jsonl'), 'a') as f:
    f.write(json.dumps(sys.argv[1:]) + '\\n')
p = os.path.join(d, 'pre.rc')
sys.exit(int(open(p).read()) if os.path.exists(p) else 0)
'''

LOCK_HOLDER = '''import fcntl, math, os, sys, time
f = open(sys.argv[1], 'a+')
fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
base = math.ceil(time.time())
f.seek(0)
f.truncate()
f.write('%d %d %d\\n' % (os.getpid(), base + int(sys.argv[2]), base + int(sys.argv[3])))
f.flush()
print('ready', flush=True)
time.sleep(120)
'''


def init(model):
    return {'emit': {'type': 'system', 'subtype': 'init', 'model': model}}


def assistant(model, text='working'):
    return {'emit': {'type': 'assistant', 'message': {'model': model, 'content': [{'type': 'text', 'text': text}]}}}


def result(is_error=False, cost=0.25, turns=3, models=(MODEL,), text='all done', usage=None):
    event = {'type': 'result', 'subtype': 'error' if is_error else 'success', 'is_error': is_error,
             'total_cost_usd': cost, 'num_turns': turns, 'result': text,
             'modelUsage': usage if usage is not None else {m: {'inputTokens': 1, 'costUSD': 0.01} for m in models}}
    return {'emit': event}


def ok_steps(model=MODEL, **kw):
    return [init(model), assistant(model), result(models=(model,), **kw)]


def quota_event(session=10, week=10, status='allowed', **info):
    windows = {'five_hour': {'utilization': session / 100}, 'seven_day': {'utilization': week / 100}}
    info = {'status': status, 'unifiedWindows': windows, **info}
    return {'emit': {'type': 'rate_limit_event', 'rate_limit_info': info}}


def profile_entry(session=10, week=10, ok=True, resets=None):
    quota = {'session': {'pct': session}, 'week_all': {'pct': week}}
    if resets:
        quota['session']['resets_at'], quota['week_all']['resets_at'] = resets
    return {'ok': ok, 'quota': quota}


def usage_doc(claude=None, **other_agents):
    agents = {'claude': {'profiles': claude if claude is not None else {'personal': profile_entry()}}}
    for name, profiles in other_agents.items():
        agents[name] = {'profiles': profiles}
    return {'agents': agents}


def flag(args, name):
    return args[args.index(name) + 1]


def flag_values(args, name):
    """Values after name up to the next --flag (an option may take one or several arguments)."""
    out = []
    for a in args[args.index(name) + 1:]:
        if a.startswith('--'):
            break
        out.append(a)
    return out


class Result:
    def __init__(self, proc, pid, out, err, seconds):
        self.pid, self.out, self.err, self.seconds = pid, out, err, seconds
        self.code = proc.returncode


class CuratorCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='curator-test-'))
        self.addCleanup(subprocess.run, ['rm', '-rf', str(self.tmp)])
        self.home = self.tmp / 'home'
        self.fakes = self.tmp / 'fakes'
        self.state = self.tmp / 'state'
        self.chome = self.tmp / 'curator'
        self.act = self.tmp / 'activity'
        for d in (self.home, self.fakes, self.state, self.chome / 'passes', self.act):
            d.mkdir(parents=True)
        self.thresholds = self.tmp / 'thresholds.conf'
        self.thresholds.write_text('QUOTA_GO_MAX=80\nQUOTA_PARK=90\nQUOTA_CARRY=95\n')
        py = sys.executable
        self.sessioneer = self.fake('sessioneer', FAKE_SESSIONEER.replace('__PY__', py))
        self.dibs = self.fake('dibs', FAKE_DIBS.replace('__PY__', py))
        self.claude = self.fake('claude', FAKE_CLAUDE.replace('__PY__', py))
        self.precheck = self.fake('precheck', FAKE_PRECHECK.replace('__PY__', py))
        self.write_conf()
        self.set_candidates(
            'mechanical claude personal claude-haiku-5-5 low\n'
            'balanced   claude personal claude-sonnet-5-5 medium\n'
            'advanced   claude personal claude-opus-5-5 high\n')
        (self.chome / 'base.md').write_text(
            'BASE-MARKER pass={pass} run={run_id} runs={runs_issue} proposals={proposals_issue} '
            'model={model} LAST_OK=<{last_ok}>\n')
        self.write_pass('light', body='BODY-MARKER {pass} {run_id}\nCount the things.\n')
        self.write_pass('heavy', tier='advanced', headers={'Timeout-min': 30, 'Budget-usd': 1})
        self.set_list({'ok': True, 'sessions': []})
        self.set_usage(usage_doc())
        self.set_dibs({'tasks': [], 'next_id': 100})
        self.scenario(ok_steps())
        self.env_extra = {}
        self.env_drop = set()
        self.holders = []
        self.addCleanup(self.stop_holders)

    # fakes and files

    def fake(self, name, source):
        path = self.fakes / name
        path.write_text(source)
        path.chmod(0o755)
        return path

    def write_conf(self, **overrides):
        values = {'ACTIVE_MIN': 30, 'ACTIVITY_PATHS': '~/.claude/projects:~/.claude-work/projects:~/.codex/sessions',
                  'PROBE_TIMEOUT_SEC': 30, 'HEARTBEAT_SEC': 1, 'LOG_DAYS': 14,
                  'LOG_KEEP': 200, 'DIBS_AREA': 2, 'DIBS_GROUP': 'AI workflows', 'TOOL_PATHS': str(self.tmp)}
        values.update(overrides)
        (self.chome / 'curator.conf').write_text(
            '# test config\n' + ''.join(f'{k}={v}\n' for k, v in values.items() if v is not None))

    def tool_path(self, *parts):
        """(Tools spec path, absolute path) for a directory under the temp dir; `//` plus the path without its slash."""
        absolute = str(self.tmp.joinpath(*parts))
        return '/' + absolute + '/**', absolute

    def set_candidates(self, text):
        (self.chome / 'candidates.txt').write_text(text)

    def write_pass(self, name, tier='balanced', headers=None, body='BODY {pass}\n', sep=True):
        h = {'Tier': tier, 'Timeout-min': 20, 'Budget-usd': 0.5}
        h.update(headers or {})
        text = ''.join(f'{k}: {v}\n' for k, v in h.items() if v is not None)
        text += ('---\n' if sep else '') + body
        (self.chome / 'passes' / f'{name}.md').write_text(text)

    def set_list(self, doc, raw=False, rc=0):
        (self.fakes / 'list.json').write_text(doc if raw else json.dumps(doc))
        (self.fakes / 'list.rc').write_text(str(rc))

    def set_usage(self, doc):
        (self.fakes / 'usage.json').write_text(json.dumps(doc))

    def set_dibs(self, state):
        state.setdefault('tasks', [])
        (self.fakes / 'dibs_state.json').write_text(json.dumps(state))

    def dibs_state(self):
        return json.loads((self.fakes / 'dibs_state.json').read_text())

    def update_dibs(self, **kw):
        s = self.dibs_state()
        s.update(kw)
        self.set_dibs(s)

    def standing(self, extra=()):
        tasks = [{'id': RUNS_ID, 'title': 'Curator runs', 'state': 'OPEN', 'labels': ['curator'], 'modifiedAt': None},
                 {'id': PROPOSALS_ID, 'title': 'Curator proposals', 'state': 'OPEN', 'labels': ['curator'],
                  'modifiedAt': None}]
        state = self.dibs_state()
        state['tasks'] = tasks + list(extra)
        self.set_dibs(state)

    def rule(self, i, modified='2026-01-01T00:00:00Z'):
        return {'id': i, 'title': f'Rule {i}', 'state': 'OPEN', 'labels': ['rule'], 'modifiedAt': modified}

    def scenario(self, steps, exit_code=0):
        (self.fakes / 'claude_scenario.json').write_text(json.dumps({'steps': steps, 'exit': exit_code}))

    def lines(self, name):
        p = self.fakes / name
        return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []

    def dibs_calls(self, *cmds):
        calls = self.lines('dibs.jsonl')
        return [c for c in calls if not cmds or c['cmd'] in cmds]

    def dibs_writes(self):
        return [c for c in self.lines('dibs.jsonl') if c['cmd'] in WRITE_CMDS]

    def claude_calls(self):
        return self.lines('claude.jsonl')

    def probe_calls(self):
        return self.lines('probe.jsonl')

    def probe_scenario(self, events=(), exit_code=0, sleep=0):
        (self.fakes / 'probe_scenario.json').write_text(
            json.dumps({'events': list(events), 'exit': exit_code, 'sleep': sleep}))

    def sessioneer_calls(self):
        return self.lines('sessioneer.jsonl')

    def last_file(self, name='light'):
        p = self.state / f'last-{name}.json'
        return json.loads(p.read_text()) if p.exists() else None

    def write_last(self, name='light', **kw):
        doc = {'finished_at': int(time.time()), 'outcome': 'ok', 'ok_at': int(time.time())}
        doc.update(kw)
        (self.state / f'last-{name}.json').write_text(json.dumps(doc))

    # running the curator

    def env(self):
        env = {'PATH': '/usr/bin:/bin', 'HOME': str(self.home), 'PYTHONDONTWRITEBYTECODE': '1',
               'CURATOR_HOME': str(self.chome), 'CURATOR_STATE_DIR': str(self.state),
               'CURATOR_SESSIONEER': str(self.sessioneer), 'DIBS_CLI': str(self.dibs),
               'CURATOR_CLAUDE': str(self.claude), 'SESSION_FLOW_THRESHOLDS': str(self.thresholds),
               'CURATOR_ACTIVITY_PATHS': str(self.act)}
        env.update(self.env_extra)
        for k in self.env_drop:
            env.pop(k, None)
        return env

    def start(self, *args):
        return subprocess.Popen([sys.executable, str(SCRIPT), *args], env=self.env(), cwd=str(self.tmp),
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def finish(self, proc, started, timeout=90):
        try:
            out, err = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, err = proc.communicate()
            self.fail(f'curator did not finish in {timeout}s\nstdout={out}\nstderr={err}')
        if not SCRIPT.exists():
            self.fail(f'{SCRIPT} does not exist yet')
        return Result(proc, proc.pid, out, err, time.time() - started)

    def curator(self, *args, timeout=90):
        started = time.time()
        return self.finish(self.start(*args), started, timeout)

    def run_pass(self, name='light', *extra, **kw):
        return self.curator('run', '--pass', name, *extra, **kw)

    def gate(self, name='light', **kw):
        r = self.curator('gate', '--pass', name, '--json', **kw)
        try:
            doc = json.loads(r.out)
        except ValueError:
            self.fail(f'gate --json did not print one JSON value\nstdout={r.out!r}\nstderr={r.err!r}')
        return r, doc

    def assert_skipped_by_gate(self, reason_start, name='light'):
        r, doc = self.gate(name)
        self.assertEqual(r.code, 1, r.out + r.err)
        self.assertIs(doc['run'], False)
        self.assertTrue(doc['reason'].startswith(reason_start), doc['reason'])
        self.assertIsNone(doc['candidate'])
        run = self.run_pass(name)
        self.assertEqual(run.code, 0, run.out + run.err)
        self.assertIn(reason_start, run.out)
        self.assertEqual(self.claude_calls(), [])
        self.assertEqual(self.dibs_writes(), [])

    def assert_would_run(self, name='light'):
        r, doc = self.gate(name)
        self.assertEqual(r.code, 0, r.out + r.err)
        self.assertIs(doc['run'], True, doc)
        return doc

    # lock holders

    def hold_lock(self, start_offset=0, deadline_offset=600, script_name='curator.py'):
        """A process holding the flock; the file says it started start_offset s from now, due at deadline_offset."""
        d = self.tmp / f'holder-{len(self.holders)}'
        d.mkdir()
        script = d / script_name
        script.write_text(LOCK_HOLDER)
        p = subprocess.Popen([sys.executable, str(script), str(self.state / 'curator.lock'),
                              str(start_offset), str(deadline_offset)],
                             env=self.env(), stdout=subprocess.PIPE, stdin=subprocess.DEVNULL, text=True,
                             start_new_session=True)
        self.holders.append(p)
        self.assertEqual(p.stdout.readline().strip(), 'ready')
        return p

    def stop_holders(self):
        for p in self.holders:
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            p.wait()
            if p.stdout:
                p.stdout.close()

    def wait_dead(self, pid, seconds=5):
        end = time.time() + seconds
        while time.time() < end:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return True
            try:
                with open(f'/proc/{pid}/stat') as f:
                    if f.read().rsplit(')', 1)[1].split()[0] == 'Z':
                        return True
            except OSError:
                return True
            time.sleep(0.1)
        return False

    def assert_released(self, result, outcome_start=None):
        releases = self.dibs_calls('todo:agent:release')
        self.assertEqual(len(releases), 1, self.dibs_calls())
        args = releases[0]['args']
        self.assertEqual(args[0], str(RUNS_ID))
        self.assertEqual(flag(args, '--token'), TOKEN)
        self.assertEqual(flag(args, '--pid'), str(result.pid))
        left = flag(args, '--left')
        self.assertRegex(left, r'^Curator run \d{8}-\d{6}-\w+ finished: ')
        if outcome_start:
            self.assertIn('finished: ' + outcome_start, left)
        return left

    def report_body(self):
        comments = self.dibs_calls('todo:agent:comment')
        self.assertEqual(len(comments), 1, self.dibs_calls())
        return flag(comments[0]['args'], '--body')


class ConfigurationTests(CuratorCase):
    """Config and pass-file validation: every bad input exits 2 and launches or writes nothing."""

    def assert_config_error(self, name='light'):
        for args in (('run', '--pass', name), ('gate', '--pass', name)):
            with self.subTest(args=args):
                r = self.curator(*args)
                self.assertEqual(r.code, 2, r.out + r.err)
        self.assertEqual(self.claude_calls(), [])
        self.assertEqual(self.dibs_writes(), [])

    def test_missing_pass_file(self):
        self.assert_config_error('nope')

    def test_missing_separator_line(self):
        self.write_pass('light', sep=False)
        self.assert_config_error()

    def test_missing_tier(self):
        self.write_pass('light', headers={'Tier': None})
        self.assert_config_error()

    def test_unknown_tier(self):
        self.write_pass('light', tier='extreme')
        self.assert_config_error()

    def test_bad_numbers(self):
        for key in ('Timeout-min', 'Budget-usd', 'Min-interval-min'):
            with self.subTest(key=key):
                self.write_pass('light', headers={key: 'abc'})
                self.assert_config_error()

    def test_tools_entries_outside_the_allowlist(self):
        good = self.tool_path('x')[0]
        bad = ['Bash', 'Edit', 'Write', 'Agent', 'WebFetch', 'Read', 'Read()', f'Read({good[:-3]})',
               'Read(tmp/x/**)', 'Grep', 'mcp__other__todo_show', 'Bash(ls)', f'Read({good}), Bash']
        for entry in bad:
            with self.subTest(entry=entry):
                self.write_pass('light', headers={'Tools': entry})
                self.assert_config_error()

    def test_valid_tools_are_accepted(self):
        a, b, c = (self.tool_path(n)[0] for n in 'abc')
        self.write_pass('light', headers={
            'Tools': f'Read({a}), Grep({b}),Glob({c}) , mcp__dibs__todo_show'})
        self.standing()
        self.assert_would_run()

    def test_tools_paths_must_be_under_tool_paths(self):
        inside = self.tool_path('a')[0]
        cases = {
            'filesystem root': 'Read(//**)',
            'other directory': 'Grep(//etc/**)',
            'sibling with the same prefix': f'Read({self.tool_path("a-sibling")[0]})',
            'parent of the allowed dir': f'Glob(/{self.tmp.parent}/**)',
        }
        self.write_conf(TOOL_PATHS=str(self.tmp / 'a'))
        self.write_pass('light', headers={'Tools': f'Read({inside})'})
        self.standing()
        self.assert_would_run()
        for label, entry in cases.items():
            with self.subTest(label):
                self.write_pass('light', headers={'Tools': entry})
                self.assert_config_error()

    def test_the_tool_path_itself_and_a_subdirectory_are_allowed(self):
        self.write_conf(TOOL_PATHS=str(self.tmp / 'a'))
        self.write_pass('light', headers={'Tools': f'Read({self.tool_path("a")[0]}), Grep({self.tool_path("a", "b", "c")[0]})'})
        self.standing()
        self.assert_would_run()

    def test_tool_paths_accepts_several_directories_and_expands_home(self):
        self.write_conf(TOOL_PATHS=f'{self.tmp / "zzz"}:~/proj')
        self.write_pass('light', headers={'Tools': f'Read(/{self.home}/proj/sub/**)'})
        self.standing()
        self.assert_would_run()

    def test_default_tool_paths_are_www_and_dotfiles_under_home(self):
        self.write_conf(TOOL_PATHS=None)
        self.standing()
        for ok in ('www/app', 'dotfiles/ai'):
            with self.subTest(ok):
                self.write_pass('light', headers={'Tools': f'Read(/{self.home}/{ok}/**)'})
                self.assert_would_run()
        self.write_pass('light', headers={'Tools': f'Read(/{self.home}/elsewhere/**)'})
        self.assert_config_error()

    def test_bad_number_in_conf(self):
        self.write_conf(ACTIVE_MIN='abc')
        self.assert_config_error()

    def test_unknown_conf_keys_and_comments_are_ignored(self):
        with open(self.chome / 'curator.conf', 'a') as f:
            f.write('SOMETHING_NEW=whatever\n  # indented comment\n')
        self.standing()
        self.assert_would_run()

    def test_duplicate_standing_issue_title_is_a_configuration_error(self):
        self.standing(extra=[{'id': 55, 'title': 'Curator runs', 'state': 'OPEN', 'labels': [], 'modifiedAt': None}])
        r = self.run_pass()
        self.assertEqual(r.code, 2, r.out + r.err)
        self.assertEqual(self.claude_calls(), [])
        self.assertEqual(self.dibs_calls('todo:agent:claim'), [])

    def test_duplicate_proposals_title_is_a_configuration_error(self):
        self.standing(extra=[{'id': 56, 'title': 'Curator proposals', 'state': 'OPEN', 'labels': [], 'modifiedAt': None}])
        r = self.run_pass()
        self.assertEqual(r.code, 2, r.out + r.err)
        self.assertEqual(self.claude_calls(), [])

    def test_config_error_is_decided_before_the_lock(self):
        self.write_pass('light', tier='extreme')
        self.hold_lock()
        self.assertEqual(self.run_pass().code, 2)


class LockTests(CuratorCase):
    """One flock for all passes. Stale = past its deadline, argv[1] is curator.py, started no later than recorded."""

    def test_live_holder_means_already_running(self):
        holder = self.hold_lock()
        self.assert_skipped_by_gate('already running')
        self.assertIsNone(holder.poll())

    def test_lock_is_shared_by_every_pass(self):
        self.hold_lock()
        self.assert_skipped_by_gate('already running', name='heavy')

    def test_holder_past_its_deadline_without_a_curator_script_is_left_alone(self):
        holder = self.hold_lock(deadline_offset=-60, script_name='other.py')
        self.assert_skipped_by_gate('already running')
        self.assertIsNone(holder.poll())

    def test_holder_whose_script_only_ends_like_curator_is_left_alone(self):
        holder = self.hold_lock(deadline_offset=-60, script_name='notcurator.py')
        self.assert_skipped_by_gate('already running')
        self.assertIsNone(holder.poll())

    def test_holder_inside_its_deadline_is_not_killed(self):
        holder = self.hold_lock(deadline_offset=600)
        self.assert_skipped_by_gate('already running')
        self.assertIsNone(holder.poll())

    def test_process_that_started_after_the_recorded_start_is_not_the_holder(self):
        holder = self.hold_lock(start_offset=-3600, deadline_offset=-60)
        self.assert_skipped_by_gate('already running')
        self.assertIsNone(holder.poll())

    def test_stale_curator_holder_is_terminated_and_the_lock_taken(self):
        holder = self.hold_lock(deadline_offset=-60)
        self.standing()
        r = self.run_pass()
        self.assertEqual(r.code, 0, r.out + r.err)
        self.assertTrue(self.wait_dead(holder.pid), 'stale holder still alive')
        self.assertEqual(len(self.claude_calls()), 1)
        self.assertEqual(self.last_file()['outcome'], 'ok')

    def test_gate_reports_a_stale_holder_but_never_terminates_it(self):
        holder = self.hold_lock(deadline_offset=-60)
        before = (self.state / 'curator.lock').read_text()
        r, doc = self.gate()
        self.assertEqual(r.code, 1)
        self.assertTrue(doc['reason'].startswith('already running'))
        self.assertIsNone(holder.poll())
        self.assertEqual((self.state / 'curator.lock').read_text(), before)
        self.assertEqual(self.claude_calls(), [])

    def test_lock_file_holds_pid_start_and_deadline_while_running(self):
        self.standing()
        self.run_pass()
        pid, start, deadline = (int(x) for x in self.claude_calls()[0]['lock'].split())
        self.assertNotEqual(pid, 0)
        self.assertLess(abs(start - time.time()), 120)
        self.assertEqual(deadline, start + (20 + 10) * 60)

    def test_lock_file_pid_is_the_curator_process(self):
        self.standing()
        r = self.run_pass()
        self.assertEqual(int(self.claude_calls()[0]['lock'].split()[0]), r.pid)

    def test_release_truncates_the_lock_file(self):
        self.standing()
        self.assertEqual(self.run_pass().code, 0)
        self.assertEqual((self.state / 'curator.lock').read_text(), '')

    def test_gate_probe_does_not_write_the_lock_file(self):
        self.standing()
        self.assert_would_run()
        lock = self.state / 'curator.lock'
        self.assertEqual(lock.read_text() if lock.exists() else '', '')

    def test_gate_releases_its_lock_probe_at_once(self):
        self.standing()
        self.assert_would_run()
        import fcntl
        with open(self.state / 'curator.lock', 'a+') as f:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_lock_file_left_by_a_dead_process_is_ignored(self):
        (self.state / 'curator.lock').write_text('999999 1 2\n')
        self.standing()
        self.assert_would_run()

    def test_second_run_while_one_is_running_skips_and_launches_nothing(self):
        self.standing()
        self.scenario([init(MODEL), {'sleep': 3}, result()])
        started = time.time()
        first = self.start('run', '--pass', 'light')
        end = time.time() + 15
        while not self.claude_calls() and time.time() < end:
            time.sleep(0.05)
        self.assertEqual(len(self.claude_calls()), 1)
        second = self.curator('run', '--pass', 'heavy')
        self.assertEqual(second.code, 0, second.out + second.err)
        self.assertIn('already running', second.out)
        a = self.finish(first, started)
        self.assertEqual(a.code, 0, a.out + a.err)
        self.assertEqual(len(self.claude_calls()), 1)
        self.assertEqual(len(self.dibs_calls('todo:agent:claim')), 1)


class CadenceTests(CuratorCase):
    """Min-interval-min compares against ok_at only."""

    def setUp(self):
        super().setUp()
        self.standing()

    def test_recent_ok_run_skips(self):
        self.write_pass('light', headers={'Min-interval-min': 30})
        self.write_last(ok_at=int(time.time()) - 10 * 60)
        self.assert_skipped_by_gate('ran recently')

    def test_old_ok_run_does_not_skip(self):
        self.write_pass('light', headers={'Min-interval-min': 30})
        self.write_last(ok_at=int(time.time()) - 40 * 60)
        self.assert_would_run()

    def test_recent_failed_run_without_ok_at_does_not_skip(self):
        self.write_pass('light', headers={'Min-interval-min': 30})
        self.write_last(outcome='agent error', ok_at=None)
        self.assert_would_run()

    def test_no_previous_run_does_not_skip(self):
        self.write_pass('light', headers={'Min-interval-min': 30})
        self.assert_would_run()

    def test_default_interval_is_zero(self):
        self.write_last(ok_at=int(time.time()) - 5)
        self.assert_would_run()

    def test_cadence_is_per_pass(self):
        self.write_pass('light', headers={'Min-interval-min': 30})
        self.write_last('heavy', ok_at=int(time.time()))
        self.assert_would_run('light')

    def test_cadence_is_decided_before_sessioneer_is_asked(self):
        self.write_pass('light', headers={'Min-interval-min': 30})
        self.write_last(ok_at=int(time.time()))
        self.assert_skipped_by_gate('ran recently')
        self.assertEqual(self.sessioneer_calls(), [])

    def test_lock_is_decided_before_cadence(self):
        self.write_pass('light', headers={'Min-interval-min': 30})
        self.write_last(ok_at=int(time.time()))
        self.hold_lock()
        self.assert_skipped_by_gate('already running')


class SessionGateTests(CuratorCase):
    """sessioneer --list --json decides whether someone is working."""

    def setUp(self):
        super().setUp()
        self.standing()

    def test_list_command_shape(self):
        self.assert_would_run()
        first = self.sessioneer_calls()[0]
        self.assertIn('--list', first)
        self.assertIn('--json', first)

    def test_sessioneer_unavailable_variants(self):
        variants = {
            'non-zero exit': dict(doc='{"ok": true, "sessions": []}', raw=True, rc=1),
            'not json': dict(doc='sessioneer is broken', raw=True, rc=0),
            'ok false': dict(doc={'ok': False, 'sessions': []}),
            'ok missing': dict(doc={'sessions': []}),
            'sessions missing': dict(doc={'ok': True}),
            'sessions not a list': dict(doc={'ok': True, 'sessions': 'none'}),
            'empty output': dict(doc='', raw=True, rc=0),
        }
        for label, kw in variants.items():
            with self.subTest(label):
                self.set_list(**kw)
                self.assert_skipped_by_gate('sessioneer unavailable')

    def test_idle_and_blocked_sessions_do_not_block(self):
        self.set_list({'ok': True, 'sessions': [{'name': 'a', 'status': 'idle'}, {'name': 'b', 'status': 'blocked'}]})
        self.assert_would_run()

    def test_other_statuses_are_active(self):
        for status in ('working', 'busy', 'running', 'starting'):
            with self.subTest(status):
                self.set_list({'ok': True, 'sessions': [{'name': 'a', 'status': 'idle'},
                                                        {'name': 'worker-1', 'status': status}]})
                r, doc = self.gate()
                self.assertEqual(r.code, 1)
                self.assertEqual(doc['reason'], f'session active: worker-1 ({status})')

    def test_session_with_curator_tag_is_ignored(self):
        self.set_list({'ok': True, 'sessions': [{'name': 'nightly', 'status': 'working', 'tags': ['curator']}]})
        self.assert_would_run()

    def test_session_with_curator_name_prefix_is_ignored(self):
        self.set_list({'ok': True, 'sessions': [{'name': '[curator] light 20260101-000000', 'status': 'working'}]})
        self.assert_would_run()

    def test_other_tags_and_inner_curator_text_are_not_ignored(self):
        self.set_list({'ok': True, 'sessions': [{'name': 'x [curator]', 'status': 'working', 'tags': ['other']}]})
        r, doc = self.gate()
        self.assertEqual(r.code, 1)
        self.assertTrue(doc['reason'].startswith('session active: x [curator]'))

    def test_ignored_session_does_not_hide_a_real_one(self):
        self.set_list({'ok': True, 'sessions': [{'name': '[curator] a', 'status': 'working'},
                                                {'name': 'real', 'status': 'working', 'tags': []}]})
        r, doc = self.gate()
        self.assertEqual(doc['reason'], 'session active: real (working)')

    def test_sessioneer_is_decided_before_activity(self):
        self.set_list({'ok': True, 'sessions': [{'name': 'real', 'status': 'working'}]})
        f = self.act / 'x.jsonl'
        f.write_text('x')
        r, doc = self.gate()
        self.assertTrue(doc['reason'].startswith('session active'))

    def test_unavailable_is_decided_before_activity(self):
        self.set_list('boom', raw=True, rc=2)
        (self.act / 'x.jsonl').write_text('x')
        r, doc = self.gate()
        self.assertTrue(doc['reason'].startswith('sessioneer unavailable'))


class ActivityTests(CuratorCase):
    """Newest file mtime under ACTIVITY_PATHS."""

    def setUp(self):
        super().setUp()
        self.standing()

    def touch(self, path, minutes_ago):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('x')
        t = time.time() - minutes_ago * 60
        os.utime(path, (t, t))

    def test_recent_file_blocks_and_reports_its_age(self):
        self.touch(self.act / 'proj' / 'deep' / 's.jsonl', 12)
        r, doc = self.gate()
        self.assertEqual(r.code, 1)
        self.assertTrue(doc['reason'].startswith('recent activity'), doc['reason'])
        self.assertIn('12', doc['reason'])
        self.assert_skipped_by_gate('recent activity')

    def test_old_files_do_not_block(self):
        self.touch(self.act / 'a' / 's.jsonl', 45)
        self.touch(self.act / 'b' / 's.jsonl', 600)
        self.assert_would_run()

    def test_newest_file_decides(self):
        self.touch(self.act / 'old.jsonl', 600)
        self.touch(self.act / 'new.jsonl', 3)
        self.assertTrue(self.gate()[1]['reason'].startswith('recent activity'))

    def test_active_min_is_configurable(self):
        self.touch(self.act / 's.jsonl', 45)
        self.write_conf(ACTIVE_MIN=60)
        self.assertTrue(self.gate()[1]['reason'].startswith('recent activity'))

    def test_several_paths_and_missing_ones_are_handled(self):
        other = self.tmp / 'other'
        self.touch(other / 'fresh.jsonl', 2)
        self.env_extra['CURATOR_ACTIVITY_PATHS'] = f'{self.tmp / "missing"}:{self.act}:{other}'
        self.assertTrue(self.gate()[1]['reason'].startswith('recent activity'))

    def test_only_missing_paths_means_no_activity(self):
        self.env_extra['CURATOR_ACTIVITY_PATHS'] = f'{self.tmp / "missing"}:{self.tmp / "missing2"}'
        self.assert_would_run()

    def test_conf_paths_expand_the_home_directory(self):
        self.write_conf(ACTIVITY_PATHS='~/convo')
        self.env_drop.add('CURATOR_ACTIVITY_PATHS')
        self.touch(self.home / 'convo' / 's.jsonl', 2)
        self.assertTrue(self.gate()[1]['reason'].startswith('recent activity'))

    def test_environment_overrides_conf_paths(self):
        self.write_conf(ACTIVITY_PATHS='~/convo')
        self.touch(self.home / 'convo' / 's.jsonl', 2)
        self.assert_would_run()

    def test_activity_is_decided_before_the_precheck(self):
        self.write_pass('light', headers={'Precheck': str(self.precheck)})
        self.touch(self.act / 's.jsonl', 2)
        self.assertTrue(self.gate()[1]['reason'].startswith('recent activity'))
        self.assertEqual(self.lines('pre.jsonl'), [])


class PrecheckTests(CuratorCase):
    """Precheck exit 0 runs, exit 1 is nothing to do, anything else skips."""

    def setUp(self):
        super().setUp()
        self.standing()
        self.write_pass('light', headers={'Precheck': f'{self.precheck} "two words" plain'})

    def set_rc(self, rc):
        (self.fakes / 'pre.rc').write_text(str(rc))

    def test_exit_zero_runs_and_arguments_are_split_like_a_shell_would(self):
        self.set_rc(0)
        self.assert_would_run()
        self.assertEqual(self.lines('pre.jsonl')[0], ['two words', 'plain'])
        r = self.run_pass()
        self.assertEqual(r.code, 0, r.out + r.err)
        self.assertEqual(len(self.claude_calls()), 1)

    def test_exit_one_is_nothing_to_do(self):
        self.set_rc(1)
        r = self.run_pass()
        self.assertEqual(r.code, 0, r.out + r.err)
        self.assertEqual(self.claude_calls(), [])
        self.assertEqual(self.dibs_writes(), [])
        last = self.last_file()
        self.assertEqual(last['outcome'], 'nothing to do')
        self.assertIsNotNone(last['ok_at'])
        self.assertLess(abs(last['ok_at'] - time.time()), 60)

    def test_gate_reports_nothing_to_do_without_writing_a_last_file(self):
        self.set_rc(1)
        r, doc = self.gate()
        self.assertEqual(r.code, 1)
        self.assertIs(doc['run'], False)
        self.assertEqual(doc['reason'], 'nothing to do')
        self.assertIsNone(doc['candidate'])
        self.assertIsNone(self.last_file())
        self.assertEqual(self.dibs_writes(), [])

    def test_other_exit_codes_are_a_failed_precheck(self):
        for rc in (2, 3, 127):
            with self.subTest(rc=rc):
                self.set_rc(rc)
                self.assert_skipped_by_gate('precheck failed')
                self.assertIsNone(self.last_file())

    def test_precheck_that_cannot_start_is_a_failed_precheck(self):
        self.write_pass('light', headers={'Precheck': str(self.tmp / 'no-such-command')})
        self.assert_skipped_by_gate('precheck failed')

    def test_precheck_is_decided_before_quota(self):
        self.set_rc(1)
        self.set_usage(usage_doc({'personal': profile_entry(99, 99)}))
        r = self.run_pass()
        self.assertEqual(r.code, 0)
        self.assertEqual(self.last_file()['outcome'], 'nothing to do')


class CandidateTests(CuratorCase):
    """Tier match, file order, quota probe, quota ceiling, adapter."""

    def setUp(self):
        super().setUp()
        self.standing()

    def candidate(self, name='light'):
        doc = self.assert_would_run(name)
        return json.dumps(doc['candidate'])

    def test_tier_picks_the_matching_candidate(self):
        self.assertIn('claude-sonnet-5-5', self.candidate('light'))
        self.assertIn('claude-opus-5-5', self.candidate('heavy'))
        self.write_pass('cheap', tier='mechanical')
        self.assertIn('claude-haiku-5-5', self.candidate('cheap'))

    def test_candidate_shape_carries_the_file_columns(self):
        doc = self.assert_would_run()
        self.assertEqual(set(doc), {'run', 'reason', 'candidate'})
        self.assertIsInstance(doc['reason'], str)
        self.assertEqual(doc['candidate'], {'tier': 'balanced', 'agent': 'claude', 'profile': 'personal',
                                            'model': 'claude-sonnet-5-5', 'effort': 'medium'})

    def two_balanced(self):
        self.set_candidates(
            '# preference order\n'
            'balanced claude personal model-first low\n'
            '\n'
            'balanced claude work model-second low\n')

    def launched_model(self):
        before = len(self.claude_calls())
        self.run_pass()
        calls = self.claude_calls()
        self.assertEqual(len(calls), before + 1, 'no agent launched')
        (self.state / 'last-light.json').unlink(missing_ok=True)
        return flag(calls[-1]['argv'], '--model')

    def assert_parked(self, text='no candidate with quota'):
        r = self.run_pass()
        self.assertEqual(r.code, 0, r.out + r.err)
        self.assertIn('parked: no candidate with quota', r.out)
        self.assertIn(text, r.out)
        self.assertEqual(self.claude_calls(), [])
        self.assertEqual(self.dibs_writes(), [])
        return r

    def test_file_order_is_preference(self):
        self.two_balanced()
        self.set_usage(usage_doc({'personal': profile_entry(), 'work': profile_entry()}))
        self.assertEqual(self.launched_model(), 'model-first')
        self.assertEqual(len(self.probe_calls()), 1)

    def test_later_candidate_is_used_when_the_first_does_not_qualify(self):
        cases = {
            'probe fails': {'personal': profile_entry(ok=False), 'work': profile_entry()},
            'session quota at the ceiling': {'personal': profile_entry(session=80), 'work': profile_entry()},
            'week quota above the ceiling': {'personal': profile_entry(session=5, week=85), 'work': profile_entry()},
        }
        for label, profiles in cases.items():
            with self.subTest(label):
                self.two_balanced()
                self.set_usage(usage_doc(profiles))
                self.assertEqual(self.launched_model(), 'model-second')

    def test_each_profile_is_probed_once(self):
        self.set_candidates('balanced claude personal model-a low\nbalanced claude personal model-b low\n')
        self.set_usage(usage_doc({'personal': profile_entry(99, 99)}))
        self.assert_parked()
        self.assertEqual(len(self.probe_calls()), 1)

    def test_probe_is_a_tiny_restricted_call_on_the_candidate_account(self):
        self.set_candidates('balanced claude work claude-sonnet-5-5 medium\n')
        self.set_usage(usage_doc({'work': profile_entry()}))
        self.run_pass()
        call = self.probe_calls()[0]
        args = call['argv']
        self.assertEqual(flag(args, '--model'), 'claude-haiku-5-5')
        self.assertEqual(flag(args, '--tools'), '')
        self.assertEqual(json.loads(flag(args, '--mcp-config')), {'mcpServers': {}})
        for name in ('-p', '--restricted', '--strict-mcp-config', '--no-session-persistence'):
            self.assertIn(name, args)
        self.assertEqual(flag(args, '--max-budget-usd'), '0.05')
        self.assertEqual(call['env']['CLAUDE_CONFIG_DIR'], f'{self.home}/.claude-work')

    def test_probe_model_comes_from_the_conf(self):
        self.write_conf(PROBE_MODEL='probe-x')
        self.run_pass()
        self.assertEqual(flag(self.probe_calls()[0]['argv'], '--model'), 'probe-x')

    def test_stored_sessioneer_usage_is_not_consulted(self):
        self.run_pass()
        self.assertFalse(any('--usage' in c for c in self.sessioneer_calls()))
        self.assertEqual(len(self.claude_calls()), 1)

    def test_unreadable_probe_results_park(self):
        window = {'utilization': 0.1}
        def event(**info):
            return {'type': 'rate_limit_event', 'rate_limit_info': info}
        cases = {
            'no event': ([{'type': 'result'}], 'no rate limit event'),
            'no info': ([{'type': 'rate_limit_event'}], 'quota unreadable'),
            'one window': ([event(status='allowed', unifiedWindows={'five_hour': window})], 'quota unreadable'),
            'bad utilization': ([event(status='allowed', unifiedWindows={
                'five_hour': {'utilization': 'x'}, 'seven_day': window})], 'quota unreadable'),
            'overage': ([event(status='allowed', isUsingOverage=True, unifiedWindows={
                'five_hour': window, 'seven_day': window})], 'overage'),
            'rejected': ([event(status='rejected')], 'quota 100%'),
        }
        for label, (events, text) in cases.items():
            with self.subTest(label):
                self.probe_scenario(events)
                self.assert_parked(text)

    def test_probe_timeout_parks(self):
        self.write_conf(PROBE_TIMEOUT_SEC=1)
        self.probe_scenario(sleep=20)
        r = self.assert_parked('quota probe failed: TimeoutExpired')
        self.assertLess(r.seconds, 15)

    def test_probe_that_cannot_start_parks(self):
        self.env_extra['CURATOR_CLAUDE'] = str(self.tmp / 'no-such-claude')
        self.assert_parked('quota probe failed')

    def test_gate_and_dry_run_never_probe(self):
        self.set_usage(usage_doc({'personal': profile_entry(99, 99)}))
        doc = self.assert_would_run()
        self.assertIn('probed at run time', doc['reason'])
        self.assertEqual(self.run_pass('light', '--dry-run').code, 0)
        self.assertEqual(self.probe_calls(), [])

    def test_no_probe_when_the_gate_skips(self):
        self.set_list({'ok': True, 'sessions': [{'name': 'busy', 'status': 'working'}]})
        self.run_pass()
        self.assertEqual(self.probe_calls(), [])

    def test_a_probe_result_just_inside_the_limits_qualifies(self):
        self.two_balanced()
        self.set_usage(usage_doc({'personal': profile_entry(session=79, week=79), 'work': profile_entry()}))
        self.assertEqual(self.launched_model(), 'model-first')

    def test_environment_overrides_the_thresholds_file(self):
        self.env_extra['QUOTA_GO_MAX'] = '50'
        self.set_usage(usage_doc({'personal': profile_entry(60, 10)}))
        self.assert_parked('quota 60% at or above 50%')

    def test_unknown_agent_has_no_adapter(self):
        self.set_candidates('balanced codex personal gpt-x medium\nbalanced claude personal model-claude low\n')
        self.set_usage(usage_doc(codex={'personal': profile_entry()}))
        self.assertIn('model-claude', self.candidate())

    def test_only_unknown_agents_is_parked_and_says_why(self):
        self.set_candidates('balanced codex personal gpt-x medium\n')
        self.set_usage(usage_doc(codex={'personal': profile_entry()}))
        r = self.run_pass()
        self.assertEqual(r.code, 0, r.out + r.err)
        self.assertIn('parked: no candidate with quota', r.out)
        self.assertIn('no adapter for codex', r.out)

    def test_no_candidate_for_the_tier_is_parked(self):
        self.set_candidates('mechanical claude personal claude-haiku-5-5 low\n')
        r = self.run_pass()
        self.assertEqual(r.code, 0, r.out + r.err)
        self.assertIn('parked: no candidate with quota', r.out)

    def test_parked_outcome_logs_each_reason_and_the_earliest_reset(self):
        self.two_balanced()
        self.set_usage(usage_doc({
            'personal': profile_entry(95, 10, resets=(1925035200, 1925337600)),
            'work': profile_entry(10, 95, resets=(1925028000, 1925251200))}))
        self.two_balanced()
        r = self.run_pass()
        self.assertEqual(r.code, 0, r.out + r.err)
        self.assertIn('parked: no candidate with quota', r.out)
        earliest = datetime.datetime.fromtimestamp(1925028000).astimezone().isoformat(timespec='seconds')
        self.assertIn(f'earliest reset {earliest}', r.out)
        self.assertIn('model-first', r.out)
        self.assertIn('model-second', r.out)

    def test_parked_run_writes_nothing_to_dibs_and_launches_nothing(self):
        self.set_usage(usage_doc({'personal': profile_entry(99, 99)}))
        r = self.run_pass()
        self.assertEqual(r.code, 0, r.out + r.err)
        self.assertEqual(self.dibs_writes(), [])
        self.assertEqual(self.claude_calls(), [])

    def test_parked_run_writes_the_last_file_and_keeps_the_previous_ok_at(self):
        self.write_last(outcome='ok', ok_at=1_700_000_000)
        self.set_usage(usage_doc({'personal': profile_entry(99, 99)}))
        self.assertEqual(self.run_pass().code, 0)
        last = self.last_file()
        self.assertTrue(last['outcome'].startswith('parked'), last)
        self.assertEqual(last['ok_at'], 1_700_000_000)
        self.assertGreater(last['finished_at'], 1_700_000_000)

    def test_parked_run_without_a_previous_run_has_no_ok_at(self):
        self.set_usage(usage_doc({'personal': profile_entry(99, 99)}))
        self.run_pass()
        self.assertIsNone(self.last_file()['ok_at'])

    def test_gate_json_for_a_parked_decision(self):
        self.set_candidates('balanced codex personal gpt-x medium\n')
        r, doc = self.gate()
        self.assertEqual(r.code, 1)
        self.assertIs(doc['run'], False)
        self.assertIn('no candidate with quota', doc['reason'])
        self.assertIsNone(doc['candidate'])


class GateCliTests(CuratorCase):
    """gate: read-only, exit codes, --json shape."""

    def setUp(self):
        super().setUp()
        self.standing()

    def test_would_run_prints_json_and_exits_zero(self):
        r, doc = self.gate()
        self.assertEqual(r.code, 0)
        self.assertEqual(set(doc), {'run', 'reason', 'candidate'})
        self.assertIs(doc['run'], True)
        self.assertIsInstance(doc['candidate'], dict)

    def test_would_skip_prints_json_and_exits_one(self):
        self.set_list({'ok': True, 'sessions': [{'name': 'w', 'status': 'working'}]})
        r, doc = self.gate()
        self.assertEqual(r.code, 1)
        self.assertEqual(set(doc), {'run', 'reason', 'candidate'})
        self.assertIs(doc['run'], False)
        self.assertIsNone(doc['candidate'])

    def test_plain_output_names_the_decision(self):
        r = self.curator('gate', '--pass', 'light')
        self.assertEqual(r.code, 0)
        self.assertTrue(r.out.strip())
        self.set_list({'ok': True, 'sessions': [{'name': 'w', 'status': 'working'}]})
        r = self.curator('gate', '--pass', 'light')
        self.assertEqual(r.code, 1)
        self.assertIn('session active: w (working)', r.out)

    def test_gate_is_read_only(self):
        self.assert_would_run()
        self.assertEqual(self.dibs_writes(), [])
        self.assertEqual(self.claude_calls(), [])
        self.assertIsNone(self.last_file())
        self.assertFalse((self.state / 'runs').exists() and list((self.state / 'runs').iterdir()))

    def test_gate_does_not_create_standing_issues(self):
        self.set_dibs({'tasks': [], 'next_id': 100})
        self.assert_would_run()
        self.assertEqual(self.dibs_calls('todo:agent:create'), [])


class DryRunTests(CuratorCase):
    """run --dry-run: prints the candidate, the agent command and the prompt; changes nothing."""

    def setUp(self):
        super().setUp()
        self.standing()

    def test_dry_run_prints_candidate_command_and_prompt(self):
        r = self.run_pass('light', '--dry-run')
        self.assertEqual(r.code, 0, r.out + r.err)
        self.assertIn('claude-sonnet-5-5', r.out)
        for token in ('--restricted', '--permission-mode', 'dontAsk', '--no-session-persistence', '--model'):
            self.assertIn(token, r.out)
        self.assertIn('BASE-MARKER pass=light', r.out)
        self.assertIn('BODY-MARKER light', r.out)
        self.assertIn('Count the things.', r.out)

    def test_dry_run_writes_and_launches_nothing(self):
        r = self.run_pass('light', '--dry-run')
        self.assertEqual(r.code, 0, r.out + r.err)
        self.assertEqual(self.dibs_writes(), [])
        self.assertEqual(self.claude_calls(), [])
        self.assertIsNone(self.last_file())
        runs = self.state / 'runs'
        self.assertEqual(list(runs.iterdir()) if runs.exists() else [], [])

    def test_dry_run_creates_no_standing_issues(self):
        self.set_dibs({'tasks': [], 'next_id': 100})
        r = self.run_pass('light', '--dry-run')
        self.assertEqual(r.code, 0, r.out + r.err)
        self.assertEqual(self.dibs_calls('todo:agent:create'), [])

    def test_dry_run_when_the_gate_skips_prints_the_reason_and_exits_zero(self):
        self.set_list({'ok': True, 'sessions': [{'name': 'w', 'status': 'working'}]})
        r = self.run_pass('light', '--dry-run')
        self.assertEqual(r.code, 0, r.out + r.err)
        self.assertIn('session active: w (working)', r.out)
        self.assertEqual(self.dibs_writes(), [])
        self.assertEqual(self.claude_calls(), [])
        self.assertIsNone(self.last_file())

    def test_dry_run_with_a_config_error_exits_two(self):
        self.write_pass('light', tier='extreme')
        self.assertEqual(self.run_pass('light', '--dry-run').code, 2)


class StandingIssueTests(CuratorCase):
    """The two standing issues are found by exact title or created idempotently."""

    def creates(self):
        return self.dibs_calls('todo:agent:create')

    def test_both_issues_are_created_when_missing(self):
        r = self.run_pass()
        self.assertEqual(r.code, 0, r.out + r.err)
        creates = self.creates()
        self.assertEqual(len(creates), 2)
        by_title = {c['args'][0]: c['args'] for c in creates}
        self.assertEqual(set(by_title), {'Curator runs', 'Curator proposals'})
        for title, key in (('Curator runs', 'curator:runs'), ('Curator proposals', 'curator:proposals')):
            args = by_title[title]
            self.assertEqual(flag(args, '--idempotency-key'), key)
            self.assertEqual(flag(args, '--area'), '2')
            self.assertEqual(flag(args, '--new-group'), 'AI workflows')
            self.assertEqual(flag(args, '--new-label'), 'curator')
            self.assertTrue(flag(args, '--body').strip())

    def test_area_and_group_come_from_the_conf(self):
        self.write_conf(DIBS_AREA=7, DIBS_GROUP='Other group')
        self.run_pass()
        for c in self.creates():
            self.assertEqual(flag(c['args'], '--area'), '7')
            self.assertEqual(flag(c['args'], '--new-group'), 'Other group')

    def test_created_ids_fill_the_prompt_placeholders_and_the_claim(self):
        r = self.run_pass()
        self.assertEqual(r.code, 0, r.out + r.err)
        ids = {t['title']: t['id'] for t in self.dibs_state()['tasks']}
        stdin = self.claude_calls()[0]['stdin']
        self.assertIn(f'runs={ids["Curator runs"]} proposals={ids["Curator proposals"]}', stdin)
        claim = self.dibs_calls('todo:agent:claim')[0]
        self.assertEqual(claim['args'][0], str(ids['Curator runs']))

    def test_issues_are_created_before_the_claim(self):
        self.run_pass()
        order = [c['cmd'] for c in self.dibs_writes()]
        self.assertLess(max(i for i, c in enumerate(order) if c == 'todo:agent:create'), order.index('todo:agent:claim'))

    def test_existing_issues_are_reused(self):
        self.standing()
        r = self.run_pass()
        self.assertEqual(r.code, 0, r.out + r.err)
        self.assertEqual(self.creates(), [])
        self.assertEqual(self.dibs_calls('todo:agent:claim')[0]['args'][0], str(RUNS_ID))
        self.assertIn(f'runs={RUNS_ID} proposals={PROPOSALS_ID}', self.claude_calls()[0]['stdin'])

    def test_only_the_missing_issue_is_created(self):
        state = self.dibs_state()
        state['tasks'] = [{'id': RUNS_ID, 'title': 'Curator runs', 'state': 'OPEN', 'labels': [], 'modifiedAt': None}]
        self.set_dibs(state)
        self.run_pass()
        self.assertEqual([c['args'][0] for c in self.creates()], ['Curator proposals'])

    def test_a_similar_title_does_not_count(self):
        state = self.dibs_state()
        state['tasks'] = [{'id': 9, 'title': 'Curator runs (old)', 'state': 'OPEN', 'labels': [], 'modifiedAt': None},
                          {'id': 10, 'title': 'curator proposals', 'state': 'OPEN', 'labels': [], 'modifiedAt': None}]
        self.set_dibs(state)
        self.run_pass()
        self.assertEqual({c['args'][0] for c in self.creates()}, {'Curator runs', 'Curator proposals'})


class DibsFailureTests(CuratorCase):
    """A Dibs failure before the claim is exit 2 with nothing launched; the Note line is tolerated."""

    def assert_dibs_failure_before_claim(self, r):
        self.assertEqual(r.code, 2, r.out + r.err)
        self.assertEqual(self.claude_calls(), [])
        self.assertEqual(self.dibs_calls('todo:agent:claim'), [])

    def test_list_fails(self):
        self.update_dibs(fail=['todo:agent:list'])
        self.assert_dibs_failure_before_claim(self.run_pass())

    def test_create_fails(self):
        self.update_dibs(fail=['todo:agent:create'])
        self.assert_dibs_failure_before_claim(self.run_pass())

    def test_trailing_text_other_than_the_note_is_a_failure(self):
        self.standing()
        self.update_dibs(trailing={'todo:agent:list': 'unexpected trailing text'})
        self.assert_dibs_failure_before_claim(self.run_pass())

    def test_claim_failing_with_trailing_text_is_a_failure(self):
        self.standing()
        self.update_dibs(trailing={'todo:agent:claim': 'garbage'})
        r = self.run_pass()
        self.assertNotEqual(r.code, 3)
        self.assertEqual(self.claude_calls(), [])

    def test_the_liveness_note_line_is_tolerated(self):
        self.standing()
        self.update_dibs(note=True)
        r = self.run_pass()
        self.assertEqual(r.code, 0, r.out + r.err)
        self.assertEqual(self.last_file()['outcome'], 'ok')

    def test_dibs_prefix_is_split_like_a_shell_would(self):
        self.standing()
        self.env_extra['DIBS_CLI'] = f'{self.dibs} --pre "two words"'
        r = self.run_pass()
        self.assertEqual(r.code, 0, r.out + r.err)
        self.assertEqual(self.dibs_calls()[0]['argv'][:2], ['--pre', 'two words'])


class ClaimTests(CuratorCase):
    """The claim on Curator runs."""

    def setUp(self):
        super().setUp()
        self.standing()

    def test_claim_shape(self):
        r = self.run_pass()
        self.assertEqual(r.code, 0, r.out + r.err)
        args = self.dibs_calls('todo:agent:claim')[0]['args']
        self.assertEqual(args[0], str(RUNS_ID))
        self.assertRegex(flag(args, '--agent'),
                         r'^curator:curator light \d{8}-\d{6}-light:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
        self.assertEqual(flag(args, '--pid'), str(r.pid))
        self.assertEqual(flag(args, '--minutes'), '35')

    def test_claim_minutes_follow_the_pass_timeout(self):
        self.write_pass('light', headers={'Timeout-min': 7})
        self.run_pass()
        self.assertEqual(flag(self.dibs_calls('todo:agent:claim')[0]['args'], '--minutes'), '22')

    def test_claim_and_session_ids_match(self):
        self.run_pass()
        agent = flag(self.dibs_calls('todo:agent:claim')[0]['args'], '--agent')
        session = flag(self.claude_calls()[0]['argv'], '--session-id')
        self.assertTrue(agent.endswith(':' + session))

    def test_refused_claim_skips_quietly(self):
        self.update_dibs(claim_refuse=True)
        r = self.run_pass()
        self.assertEqual(r.code, 0, r.out + r.err)
        self.assertIn('claim refused', r.out)
        self.assertEqual(self.claude_calls(), [])
        self.assertEqual(self.dibs_calls('todo:agent:comment', 'todo:agent:release'), [])

    def test_heartbeats_are_sent_with_the_token(self):
        self.scenario([init(MODEL), {'sleep': 3.5}, result()])
        r = self.run_pass()
        self.assertEqual(r.code, 0, r.out + r.err)
        beats = self.dibs_calls('todo:agent:heartbeat')
        self.assertGreaterEqual(len(beats), 1)
        for b in beats:
            self.assertEqual(b['args'][0], str(RUNS_ID))
            self.assertEqual(flag(b['args'], '--token'), TOKEN)
            self.assertEqual(flag(b['args'], '--pid'), str(r.pid))
            self.assertTrue(flag(b['args'], '--minutes').isdigit())


class LaunchTests(CuratorCase):
    """The claude adapter: argv, stdin, environment, process group, work directory."""

    def setUp(self):
        super().setUp()
        self.standing()

    def launch(self):
        r = self.run_pass()
        self.assertEqual(r.code, 0, r.out + r.err)
        calls = self.claude_calls()
        self.assertEqual(len(calls), 1)
        return calls[0]

    def test_argv_without_extra_tools(self):
        argv = self.launch()['argv']
        self.assertIn('-p', argv)
        self.assertEqual(flag(argv, '--model'), MODEL)
        self.assertEqual(flag(argv, '--effort'), 'medium')
        self.assertRegex(flag(argv, '--session-id'), r'^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$')
        for solo in ('--no-session-persistence', '--restricted', '--strict-mcp-config', '--verbose'):
            self.assertIn(solo, argv)
        self.assertEqual(flag(argv, '--permission-mode'), 'dontAsk')
        self.assertEqual(flag(argv, '--tools'), '')
        self.assertEqual(len(flag_values(argv, '--allowed-tools')), 1)
        self.assertTrue(flag(argv, '--allowed-tools').split(',')[0].startswith('mcp__dibs'))
        self.assertEqual(float(flag(argv, '--max-budget-usd')), 0.5)
        self.assertEqual(flag(argv, '--output-format'), 'stream-json')

    def test_mcp_config_names_only_the_dibs_server(self):
        argv = self.launch()['argv']
        self.assertEqual(len(flag_values(argv, '--mcp-config')), 1)
        cfg = json.loads(flag(argv, '--mcp-config'))
        self.assertEqual(list(cfg['mcpServers']), ['dibs'])

    def test_tools_allowlist_becomes_tools_and_allowed_tools(self):
        entries = [f'Read({self.tool_path("a")[0]})', f'Grep({self.tool_path("b")[0]})',
                   f'Glob({self.tool_path("c")[0]})', 'mcp__dibs__todo_show']
        self.write_pass('light', headers={'Tools': ', '.join(entries)})
        argv = self.launch()['argv']
        self.assertEqual(set(flag(argv, '--tools').split(',')), {'Read', 'Grep', 'Glob'})
        self.assertEqual(len(flag_values(argv, '--allowed-tools')), 1)
        allowed = flag(argv, '--allowed-tools').split(',')
        self.assertTrue(allowed[0].startswith('mcp__dibs'), allowed)
        for e in entries:
            self.assertIn(e, allowed)

    def test_duplicate_built_in_tools_are_listed_once(self):
        self.write_pass('light', headers={'Tools': f'Read({self.tool_path("a")[0]}), Read({self.tool_path("b")[0]})'})
        tools = flag(self.launch()['argv'], '--tools').split(',')
        self.assertEqual(tools, ['Read'])

    def test_each_path_is_also_passed_as_add_dir(self):
        entries = [f'Read({self.tool_path("a")[0]})', f'Grep({self.tool_path("b")[0]})',
                   f'Glob({self.tool_path("c")[0]})', 'mcp__dibs__todo_show']
        self.write_pass('light', headers={'Tools': ', '.join(entries)})
        argv = self.launch()['argv']
        dirs = [argv[i + 1] for i, a in enumerate(argv) if a == '--add-dir']
        self.assertEqual(sorted(set(dirs)), sorted(self.tool_path(n)[1] for n in 'abc'))

    def test_no_add_dir_without_path_tools(self):
        self.write_pass('light', headers={'Tools': 'mcp__dibs__todo_show'})
        self.assertNotIn('--add-dir', self.launch()['argv'])

    def test_effort_and_model_follow_the_candidate(self):
        self.write_pass('light', tier='advanced')
        self.scenario(ok_steps('claude-opus-5-5'))
        argv = self.launch()['argv']
        self.assertEqual(flag(argv, '--model'), 'claude-opus-5-5')
        self.assertEqual(flag(argv, '--effort'), 'high')

    def test_budget_comes_from_the_pass(self):
        self.write_pass('light', headers={'Budget-usd': 2.5})
        self.assertEqual(float(flag(self.launch()['argv'], '--max-budget-usd')), 2.5)

    def test_prompt_arrives_on_stdin_with_placeholders_filled(self):
        call = self.launch()
        stdin = call['stdin']
        run_id = re.search(r'run=(\d{8}-\d{6}-light)\b', stdin).group(1)
        self.assertIn(f'BASE-MARKER pass=light run={run_id}', stdin)
        self.assertIn(f'BODY-MARKER light {run_id}', stdin)
        self.assertIn(f'model={MODEL}', stdin)
        self.assertIn('LAST_OK=<never>', stdin)
        self.assertIn('Count the things.', stdin)
        self.assertLess(stdin.index('BASE-MARKER'), stdin.index('BODY-MARKER'))
        self.assertNotRegex(stdin, r'\{(run_id|pass|runs_issue|proposals_issue|last_ok|model)\}')
        started = datetime.datetime.strptime(run_id[:15], '%Y%m%d-%H%M%S')
        self.assertLess(abs((datetime.datetime.now() - started).total_seconds()), 120)

    def test_last_ok_is_the_iso_time_of_the_previous_ok_run(self):
        epoch = int(time.time()) - 5 * 3600
        self.write_last(ok_at=epoch)
        stdin = self.launch()['stdin']
        iso = re.search(r'LAST_OK=<([^>]+)>', stdin).group(1)
        self.assertNotEqual(iso, 'never')
        self.assertLess(abs(datetime.datetime.fromisoformat(iso).timestamp() - epoch), 2)

    def test_clean_environment_for_personal_profile(self):
        self.env_extra.update({'ANTHROPIC_API_KEY': 'leak', 'CLAUDE_CONFIG_DIR': '/leak', 'CURATOR_POISON': '1',
                               'DIBS_LESSON_PROMPT': 'on', 'DIBS_STOP_GATE': 'on'})
        env = self.launch()['env']
        self.assertEqual(env['HOME'], str(self.home))
        self.assertEqual(env['PATH'], f'{self.home}/.local/bin:/usr/local/bin:/usr/bin')
        self.assertEqual(env['DIBS_LESSON_PROMPT'], 'off')
        self.assertEqual(env['DIBS_STOP_GATE'], 'off')
        self.assertNotIn('CLAUDE_CONFIG_DIR', env)
        self.assertNotIn('ANTHROPIC_API_KEY', env)
        self.assertNotIn('CURATOR_POISON', env)
        self.assertEqual(set(env) - {'LC_CTYPE', 'PWD', 'SHLVL', '_'},
                         {'HOME', 'PATH', 'DIBS_LESSON_PROMPT', 'DIBS_STOP_GATE'})

    def test_work_profile_gets_the_work_config_dir(self):
        self.set_candidates('balanced claude work claude-sonnet-5-5 medium\n')
        self.set_usage(usage_doc({'work': profile_entry()}))
        env = self.launch()['env']
        self.assertEqual(env['CLAUDE_CONFIG_DIR'], f'{self.home}/.claude-work')
        self.assertEqual(env['DIBS_LESSON_PROMPT'], 'off')

    def test_runs_in_an_empty_work_directory_in_its_own_process_group(self):
        call = self.launch()
        self.assertEqual(call['cwd'], os.path.realpath(self.state / 'work'))
        self.assertEqual(call['listing'], [])
        self.assertEqual(call['pgrp'], call['pid'])
        self.assertEqual(call['sid'], call['pid'])
        self.assertNotEqual(call['pgrp'], call['parent_pgrp'])

    def test_claude_prefix_is_split_like_a_shell_would(self):
        self.env_extra['CURATOR_CLAUDE'] = f'{self.claude} --extra-flag "two words"'
        argv = self.launch()['argv']
        self.assertIn('--extra-flag', argv)
        self.assertIn('two words', argv)

    def test_session_ids_differ_between_runs(self):
        self.launch()
        (self.state / 'last-light.json').unlink()
        self.run_pass()
        a, b = [flag(c['argv'], '--session-id') for c in self.claude_calls()]
        self.assertNotEqual(a, b)


class ModelVerificationTests(CuratorCase):
    """The run is stopped, reported and released when the model is not the requested one."""

    def setUp(self):
        super().setUp()
        self.standing()

    def assert_mismatch(self, r, wrong, started_child=False):
        self.assertEqual(r.code, 3, r.out + r.err)
        self.assertIn(f'model mismatch: {wrong}', r.out)
        self.assertEqual(self.last_file()['outcome'], f'model mismatch: {wrong}')
        self.assertIsNone(self.last_file()['ok_at'])
        self.assertIn(f'model mismatch: {wrong}', self.report_body().splitlines()[0])
        self.assert_released(r, f'model mismatch: {wrong}')
        call = self.claude_calls()[0]
        self.assertTrue(self.wait_dead(call['pid']), 'claude still running')
        self.assertFalse((self.fakes / 'survived').exists())
        self.assertLess(r.seconds, 18)

    def test_init_with_another_model_terminates_the_run(self):
        self.scenario([{'spawn_child': 1}, init('claude-opus-5-5'), {'sleep': 40}, {'mark': 'survived'}])
        r = self.run_pass()
        self.assert_mismatch(r, 'claude-opus-5-5')
        child = int((self.fakes / 'child.pid').read_text())
        self.assertTrue(self.wait_dead(child), 'process group member survived')

    def test_assistant_message_with_another_model_terminates_the_run(self):
        self.scenario([init(MODEL), assistant('claude-haiku-5-5'), {'sleep': 40}, {'mark': 'survived'}])
        self.assert_mismatch(self.run_pass(), 'claude-haiku-5-5')

    def test_assistant_message_without_a_model_is_fine(self):
        self.scenario([init(MODEL), {'emit': {'type': 'assistant', 'message': {'content': []}}}, result()])
        r = self.run_pass()
        self.assertEqual(r.code, 0, r.out + r.err)
        self.assertEqual(self.last_file()['outcome'], 'ok')

    def other_models_line(self):
        return next(l for l in self.report_body().splitlines() if l.startswith('- Other models in usage:'))

    def test_extra_model_usage_keys_no_longer_fail_the_run(self):
        self.scenario([init(MODEL), result(usage={MODEL: {'costUSD': 0.2}, 'claude-haiku-5-5': {'costUSD': 0.05}})])
        r = self.run_pass()
        self.assertEqual(r.code, 0, r.out + r.err)
        self.assertEqual(self.last_file()['outcome'], 'ok')
        self.assertRegex(self.other_models_line(), r'^- Other models in usage: claude-haiku-5-5 \$0\.05\.?$')
        self.assert_released(r, 'ok')

    def test_several_extra_models_are_listed_with_their_cost(self):
        self.scenario([init(MODEL), result(usage={MODEL: {'costUSD': 0.2}, 'claude-haiku-5-5': {'costUSD': 0.05},
                                                  'claude-opus-5-5': {'costUSD': 1.5}})])
        self.run_pass()
        line = self.other_models_line()
        self.assertRegex(line, r'claude-haiku-5-5 \$0\.05')
        self.assertRegex(line, r'claude-opus-5-5 \$1\.50')

    def test_no_extra_models_says_none(self):
        self.run_pass()
        self.assertRegex(self.other_models_line(), r'^- Other models in usage: none\.?$')

    def test_synthetic_assistant_messages_are_ignored(self):
        self.scenario([init(MODEL), assistant('<synthetic>'), assistant(MODEL), result()])
        r = self.run_pass()
        self.assertEqual(r.code, 0, r.out + r.err)
        self.assertEqual(self.last_file()['outcome'], 'ok')
        self.assertIn(f'verified model: {MODEL}', self.report_body())

    def test_matching_model_everywhere_is_verified_in_the_report(self):
        r = self.run_pass()
        self.assertEqual(r.code, 0, r.out + r.err)
        self.assertIn(f'verified model: {MODEL}', self.report_body())

    def test_no_init_event_is_model_not_verified(self):
        self.write_last(outcome='ok', ok_at=1_700_000_000)
        self.scenario([assistant(MODEL), result()])
        r = self.run_pass()
        self.assertEqual(r.code, 3, r.out + r.err)
        self.assertIn('model not verified', r.out)
        last = self.last_file()
        self.assertEqual(last['outcome'], 'model not verified')
        self.assertEqual(last['ok_at'], 1_700_000_000)
        self.assertIn('model not verified', self.report_body().splitlines()[0])
        self.assertIn('verified model: not verified', self.report_body())
        self.assert_released(r, 'model not verified')

    def test_a_result_alone_is_model_not_verified(self):
        self.scenario([{'emit': {'type': 'result', 'subtype': 'success', 'is_error': False,
                                 'total_cost_usd': 0.1, 'num_turns': 1, 'result': 'fine'}}])
        r = self.run_pass()
        self.assertEqual(r.code, 3, r.out + r.err)
        self.assertEqual(self.last_file()['outcome'], 'model not verified')


class QuotaParkDuringRunTests(CuratorCase):
    """The agent is stopped when a rate limit event in its stream reaches QUOTA_PARK."""

    def setUp(self):
        super().setUp()
        self.standing()

    def test_quota_reaching_the_park_level_stops_the_run(self):
        self.scenario([init(MODEL), quota_event(95, 10),
                       {'sleep': 40}, {'emit': result()['emit']}, {'mark': 'survived'}])
        r = self.run_pass()
        self.assertEqual(r.code, 0, r.out + r.err)
        self.assertIn('parked at quota 95%', r.out)
        self.assertEqual(self.last_file()['outcome'], 'parked at quota 95%')
        self.assertIsNone(self.last_file()['ok_at'])
        self.assertTrue(self.wait_dead(self.claude_calls()[0]['pid']))
        self.assertFalse((self.fakes / 'survived').exists())
        self.assertLess(r.seconds, 18)
        self.assertIn('parked at quota 95%', self.report_body().splitlines()[0])
        self.assert_released(r, 'parked at quota 95%')

    def test_week_quota_counts_too(self):
        self.scenario([init(MODEL), quota_event(5, 92), {'sleep': 40}])
        r = self.run_pass()
        self.assertEqual(r.code, 0, r.out + r.err)
        self.assertEqual(self.last_file()['outcome'], 'parked at quota 92%')

    def test_a_rejected_status_stops_the_run(self):
        self.scenario([init(MODEL), quota_event(10, 10, status='rejected'), {'sleep': 40}])
        self.assertEqual(self.run_pass().code, 0)
        self.assertEqual(self.last_file()['outcome'], 'parked at quota 100%')

    def test_quota_below_park_does_not_stop_the_run(self):
        self.scenario([init(MODEL), quota_event(85, 10), {'sleep': 1}, result()])
        r = self.run_pass()
        self.assertEqual(r.code, 0, r.out + r.err)
        self.assertEqual(self.last_file()['outcome'], 'ok')

    def test_an_event_after_the_result_does_not_undo_the_run(self):
        self.scenario([init(MODEL), result(), quota_event(95, 95)])
        self.assertEqual(self.run_pass().code, 0)
        self.assertEqual(self.last_file()['outcome'], 'ok')

    def test_unreadable_quota_event_during_the_run_does_not_terminate_it(self):
        bad = {'type': 'rate_limit_event', 'rate_limit_info': 'garbage'}
        partial = {'type': 'rate_limit_event',
                   'rate_limit_info': {'unifiedWindows': {'five_hour': {'utilization': 0.95}}}}
        self.scenario([init(MODEL), {'emit': bad}, {'emit': partial}, {'sleep': 1}, result()])
        r = self.run_pass()
        self.assertEqual(r.code, 0, r.out + r.err)
        self.assertEqual(self.last_file()['outcome'], 'ok')

    def test_park_level_comes_from_the_thresholds_file(self):
        self.thresholds.write_text('QUOTA_GO_MAX=80\nQUOTA_PARK=97\n')
        self.scenario([init(MODEL), quota_event(95, 10), {'sleep': 1}, result()])
        self.assertEqual(self.run_pass().code, 0)
        self.assertEqual(self.last_file()['outcome'], 'ok')

    def test_park_level_can_be_overridden_by_the_environment(self):
        self.env_extra['QUOTA_PARK'] = '50'
        self.scenario([init(MODEL), quota_event(60, 10), {'sleep': 40}])
        self.assertEqual(self.run_pass().code, 0)
        self.assertEqual(self.last_file()['outcome'], 'parked at quota 60%')


class TimeoutTests(CuratorCase):
    """Timeout-min takes positive decimals; the wall clock stops the agent."""

    def setUp(self):
        super().setUp()
        self.standing()

    def test_run_over_the_timeout_is_terminated(self):
        self.write_pass('light', headers={'Timeout-min': 0.05})
        self.write_last(ok_at=1_700_000_000)
        self.scenario([init(MODEL), {'spawn_child': 1}, {'sleep': 40}, {'mark': 'survived'}])
        r = self.run_pass()
        self.assertEqual(r.code, 3, r.out + r.err)
        self.assertIn('timeout', r.out)
        last = self.last_file()
        self.assertEqual(last['outcome'], 'timeout')
        self.assertEqual(last['ok_at'], 1_700_000_000)
        self.assertTrue(self.wait_dead(self.claude_calls()[0]['pid']))
        self.assertTrue(self.wait_dead(int((self.fakes / 'child.pid').read_text())))
        self.assertFalse((self.fakes / 'survived').exists())
        self.assertLess(r.seconds, 25)
        self.assertIn(', timeout.', self.report_body().splitlines()[0])
        self.assert_released(r, 'timeout')

    def test_a_run_inside_the_timeout_is_not_stopped(self):
        self.write_pass('light', headers={'Timeout-min': 0.5})
        self.scenario([init(MODEL), {'sleep': 1.5}, result()])
        r = self.run_pass()
        self.assertEqual(r.code, 0, r.out + r.err)
        self.assertEqual(self.last_file()['outcome'], 'ok')

    def test_decimal_timeout_and_interval_are_accepted(self):
        self.write_pass('light', headers={'Timeout-min': 0.05, 'Min-interval-min': 0.5})
        self.assert_would_run()

    def test_zero_or_negative_timeout_is_a_configuration_error(self):
        for value in ('0', '-5', '-0.5'):
            with self.subTest(value=value):
                self.write_pass('light', headers={'Timeout-min': value})
                for args in (('run', '--pass', 'light'), ('gate', '--pass', 'light')):
                    self.assertEqual(self.curator(*args).code, 2)
        self.assertEqual(self.claude_calls(), [])


class OutcomeTests(CuratorCase):
    """Agent error and rule-record detection."""

    def setUp(self):
        super().setUp()
        self.standing(extra=[self.rule(7), self.rule(8),
                             {'id': 30, 'title': 'a plan', 'state': 'OPEN', 'labels': ['plan'], 'modifiedAt': 'x'}])

    def test_is_error_result_is_an_agent_error(self):
        self.scenario([init(MODEL), result(is_error=True, text='boom')])
        r = self.run_pass()
        self.assertEqual(r.code, 3, r.out + r.err)
        self.assertEqual(self.last_file()['outcome'], 'agent error')
        self.assertIsNone(self.last_file()['ok_at'])
        self.assert_released(r, 'agent error')

    def test_no_result_event_is_an_agent_error(self):
        self.scenario([init(MODEL), assistant(MODEL)], exit_code=1)
        r = self.run_pass()
        self.assertEqual(r.code, 3, r.out + r.err)
        self.assertEqual(self.last_file()['outcome'], 'agent error')
        self.assert_released(r)

    def test_unchanged_rule_records_mean_ok(self):
        r = self.run_pass()
        self.assertEqual(r.code, 0, r.out + r.err)
        self.assertIn('Rule records changed: none', self.report_body())
        self.assertGreaterEqual(len(self.dibs_calls('todo:agent:list')), 2)

    def test_changed_rule_record_overrides_ok(self):
        self.scenario(ok_steps()[:2] + [{'rules': {'change': [7]}}, ok_steps()[2]])
        r = self.run_pass()
        self.assertEqual(r.code, 3, r.out + r.err)
        self.assertEqual(self.last_file()['outcome'], 'rule records changed: 7')
        self.assertIsNone(self.last_file()['ok_at'])
        self.assertIn('Rule records changed: 7', self.report_body())
        self.assert_released(r, 'rule records changed: 7')

    def test_added_and_removed_rule_records_are_detected(self):
        self.scenario(ok_steps()[:2] + [{'rules': {'add': [99], 'remove': [8]}}, ok_steps()[2]])
        r = self.run_pass()
        self.assertEqual(r.code, 3, r.out + r.err)
        outcome = self.last_file()['outcome']
        self.assertTrue(outcome.startswith('rule records changed: '), outcome)
        self.assertIn('99', outcome)
        self.assertIn('8', outcome.split(': ', 1)[1])

    def test_changes_to_records_that_are_not_rules_are_ignored(self):
        self.scenario(ok_steps()[:2] + [{'rules': {'touch_other': [30]}}, ok_steps()[2]])
        r = self.run_pass()
        self.assertEqual(r.code, 0, r.out + r.err)
        self.assertEqual(self.last_file()['outcome'], 'ok')

    def test_rule_snapshot_is_taken_before_the_launch(self):
        self.run_pass()
        calls = [c['cmd'] for c in self.dibs_calls()]
        first_list_after_claim = calls.index('todo:agent:list', calls.index('todo:agent:claim'))
        self.assertLess(first_list_after_claim, calls.index('todo:agent:comment'))


class ReportTests(CuratorCase):
    """One comment on Curator runs with the Contract's layout."""

    def setUp(self):
        super().setUp()
        self.standing()

    def test_report_layout_for_an_ok_run(self):
        self.scenario([init(MODEL), assistant(MODEL),
                       quota_event(20, 33),
                       result(cost=0.25, turns=3, text='Open drafts: 4\nDropped tasks: 2')])
        self.set_usage(usage_doc({'personal': profile_entry(10, 5)}))
        r = self.run_pass()
        self.assertEqual(r.code, 0, r.out + r.err)
        comments = self.dibs_calls('todo:agent:comment')
        self.assertEqual(len(comments), 1)
        args = comments[0]['args']
        self.assertEqual(args[0], str(RUNS_ID))
        body = flag(args, '--body')
        run_id = re.match(r'^Curator run (\d{8}-\d{6}-light): light pass, ok\.$', body.splitlines()[0]).group(1)
        self.assertEqual(flag(args, '--idempotency-key'), f'curator:report:{run_id}')
        self.assertRegex(body, r'(?m)^- Started \d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\S*, took \d+m\d+s\.?$')
        self.assertRegex(body, rf'(?m)^- Agent: claude personal {MODEL} medium; verified model: {MODEL}\.?$')
        self.assertRegex(body, r'(?m)^- Cost: \$0\.25 over 3 turns; quota 10% to 33%\.?$')
        self.assertRegex(body, r'(?m)^- Rule records changed: none\.?$')
        log = self.state / 'runs' / f'{run_id}.jsonl'
        errlog = self.state / 'runs' / f'{run_id}.stderr'
        log_line = next(l for l in body.splitlines() if l.startswith('- Log:'))
        self.assertIn(str(log), log_line)
        self.assertIn(str(errlog), log_line)
        self.assertTrue(log.exists())
        self.assertTrue(errlog.exists())
        self.assertIn('\nPass summary:\nOpen drafts: 4\nDropped tasks: 2', body)

    def test_cost_is_two_decimals_and_quota_a_whole_percent(self):
        self.scenario([init(MODEL), result(cost=0.4567, turns=12),
                       quota_event(33.6, 20.2)])
        self.set_usage(usage_doc({'personal': profile_entry(10.4, 5)}))
        self.run_pass()
        self.assertRegex(self.report_body(), r'(?m)^- Cost: \$0\.46 over 12 turns; quota \d+% to \d+%\.?$')

    def test_unknown_cost_and_turns_are_a_question_mark(self):
        self.scenario([init(MODEL), assistant(MODEL)])
        self.run_pass()
        cost_line = next(l for l in self.report_body().splitlines() if l.startswith('- Cost:'))
        self.assertIn('?', cost_line)

    def test_pass_summary_is_cut_to_1500_characters(self):
        self.scenario([init(MODEL), result(text='A' * 1500 + 'TAIL-MARKER' + 'B' * 2000)])
        self.run_pass()
        body = self.report_body()
        summary = body.split('Pass summary:\n', 1)[1]
        self.assertLessEqual(len(summary.rstrip('\n')), 1500)
        self.assertNotIn('TAIL-MARKER', body)
        self.assertIn('A' * 1400, summary)

    def test_report_for_a_failed_run_names_the_outcome(self):
        self.scenario([init(MODEL), result(is_error=True, text='it broke')])
        self.run_pass()
        self.assertTrue(self.report_body().startswith('Curator run '))
        self.assertIn(', agent error.', self.report_body().splitlines()[0])

    def test_report_is_posted_before_the_release(self):
        self.run_pass()
        order = [c['cmd'] for c in self.dibs_writes()]
        self.assertLess(order.index('todo:agent:comment'), order.index('todo:agent:release'))
        self.assertLess(order.index('todo:agent:claim'), order.index('todo:agent:comment'))

    def test_run_log_holds_the_raw_stream_lines(self):
        steps = ok_steps()
        self.scenario(steps)
        self.run_pass()
        run_id = re.search(r'Curator run (\S+):', self.report_body()).group(1)
        logged = (self.state / 'runs' / f'{run_id}.jsonl').read_text().splitlines()
        self.assertEqual([json.loads(l) for l in logged], [s['emit'] for s in steps])

    def test_stdout_has_a_line_for_the_gate_decision_and_the_outcome(self):
        r = self.run_pass()
        self.assertGreaterEqual(len([l for l in r.out.splitlines() if l.strip()]), 2)
        self.assertIn('ok', r.out)


class ReleaseTests(CuratorCase):
    """The claim is released whatever happens after it."""

    def setUp(self):
        super().setUp()
        self.standing()

    def test_release_after_a_good_run(self):
        r = self.run_pass()
        left = self.assert_released(r, 'ok')
        self.assertRegex(left, r'^Curator run \d{8}-\d{6}-light finished: ok$')

    def test_release_when_the_agent_cannot_be_started(self):
        (self.fakes / 'vanish_after_probe').write_text('1')
        r = self.run_pass()
        self.assertEqual(r.code, 3, r.out + r.err)
        self.assertRegex(self.last_file()['outcome'], r'^agent error: .+')
        self.assertRegex(self.report_body().splitlines()[0], r', agent error: .+\.$')
        self.assert_released(r, 'agent error: ')

    def test_release_when_the_report_cannot_be_posted(self):
        self.update_dibs(fail=['todo:agent:comment'])
        r = self.run_pass()
        self.assertEqual(r.code, 2, r.out + r.err)
        self.assert_released(r)

    def test_a_failing_release_is_exit_two(self):
        self.update_dibs(fail=['todo:agent:release'])
        r = self.run_pass()
        self.assertEqual(r.code, 2, r.out + r.err)
        self.assertEqual(len(self.dibs_calls('todo:agent:release')), 1)

    def test_release_when_heartbeats_fail(self):
        self.update_dibs(fail=['todo:agent:heartbeat'])
        self.scenario([init(MODEL), {'sleep': 2.5}, result()])
        r = self.run_pass()
        self.assertEqual(len(self.dibs_calls('todo:agent:release')), 1, r.out + r.err)
        self.assertLess(r.seconds, 30)

    def test_release_after_a_model_mismatch(self):
        self.scenario([init('claude-opus-5-5'), {'sleep': 40}])
        r = self.run_pass()
        self.assert_released(r, 'model mismatch: claude-opus-5-5')

    def test_release_after_a_quota_park(self):
        self.scenario([init(MODEL), quota_event(95, 1), {'sleep': 40}])
        r = self.run_pass()
        self.assert_released(r, 'parked at quota')

    def test_no_release_when_nothing_was_claimed(self):
        self.update_dibs(claim_refuse=True)
        self.run_pass()
        self.assertEqual(self.dibs_calls('todo:agent:release'), [])


class StateFileTests(CuratorCase):
    """last-<pass>.json and run-log pruning."""

    def setUp(self):
        super().setUp()
        self.standing()

    def test_last_file_after_an_ok_run(self):
        before = time.time()
        r = self.run_pass()
        self.assertEqual(r.code, 0, r.out + r.err)
        last = self.last_file()
        self.assertEqual(set(last), {'finished_at', 'outcome', 'ok_at'})
        self.assertEqual(last['outcome'], 'ok')
        self.assertIsInstance(last['finished_at'], (int, float))
        self.assertGreaterEqual(last['finished_at'], before - 2)
        self.assertLessEqual(last['finished_at'], time.time() + 2)
        self.assertLessEqual(abs(last['ok_at'] - last['finished_at']), 5)

    def test_last_file_after_a_failed_run_has_no_ok_at(self):
        self.scenario([init(MODEL), result(is_error=True)])
        self.run_pass()
        last = self.last_file()
        self.assertEqual(last['outcome'], 'agent error')
        self.assertIsNone(last['ok_at'])
        self.assertEqual(set(last), {'finished_at', 'outcome', 'ok_at'})

    def test_previous_ok_at_is_kept_across_a_failed_run(self):
        self.write_last(outcome='ok', ok_at=1_700_000_000)
        self.scenario([init(MODEL), result(is_error=True)])
        self.run_pass()
        last = self.last_file()
        self.assertEqual(last['outcome'], 'agent error')
        self.assertEqual(last['ok_at'], 1_700_000_000)
        self.assertGreater(last['finished_at'], 1_700_000_000)

    def test_previous_ok_at_is_kept_across_a_model_mismatch(self):
        self.write_last(outcome='ok', ok_at=1_700_000_000)
        self.scenario([init('claude-opus-5-5'), {'sleep': 40}])
        self.run_pass()
        self.assertEqual(self.last_file()['ok_at'], 1_700_000_000)

    def test_a_new_ok_run_replaces_ok_at(self):
        self.write_last(outcome='ok', ok_at=1_700_000_000)
        self.run_pass()
        last = self.last_file()
        self.assertEqual(last['outcome'], 'ok')
        self.assertGreater(last['ok_at'], 1_700_000_000)

    def test_last_files_are_per_pass(self):
        self.run_pass('light')
        self.assertIsNotNone(self.last_file('light'))
        self.assertIsNone(self.last_file('heavy'))

    def test_a_skipped_run_does_not_touch_the_last_file(self):
        self.write_pass('light', headers={'Min-interval-min': 30})
        self.write_last(outcome='ok')
        before = (self.state / 'last-light.json').read_text()
        self.assertEqual(self.run_pass().code, 0)
        self.assertEqual((self.state / 'last-light.json').read_text(), before)

    def make_logs(self, names_and_age_days):
        runs = self.state / 'runs'
        runs.mkdir(parents=True, exist_ok=True)
        for name, days in names_and_age_days:
            p = runs / name
            p.write_text('{}\n')
            t = time.time() - days * 86400
            os.utime(p, (t, t))
        return runs

    def current_log(self, runs, existing):
        new = [p for p in runs.iterdir() if p.name not in existing]
        self.assertEqual(len(new), 1, [p.name for p in runs.iterdir()])
        return new[0]

    def test_logs_older_than_log_days_are_pruned(self):
        runs = self.make_logs([('too-old.jsonl', 15), ('kept.jsonl', 13), ('fresh.jsonl', 0.1)])
        self.assertEqual(self.run_pass().code, 0)
        names = {p.name for p in runs.iterdir()}
        self.assertNotIn('too-old.jsonl', names)
        self.assertLessEqual({'kept.jsonl', 'fresh.jsonl'}, names)

    def test_log_days_is_configurable(self):
        self.write_conf(LOG_DAYS=2)
        runs = self.make_logs([('three-days.jsonl', 3), ('one-day.jsonl', 1)])
        self.run_pass()
        names = {p.name for p in runs.iterdir()}
        self.assertNotIn('three-days.jsonl', names)
        self.assertIn('one-day.jsonl', names)

    def test_at_most_log_keep_files_remain_and_the_newest_stay(self):
        self.write_conf(LOG_KEEP=3)
        existing = [(f'young-{i}.jsonl', 0.1 + i / 10) for i in range(5)]
        runs = self.make_logs(existing)
        self.assertEqual(self.run_pass().code, 0)
        remaining = {p.name for p in runs.iterdir()}
        self.assertEqual(len(remaining), 3, remaining)
        self.assertIn('young-0.jsonl', remaining)
        self.assertNotIn('young-4.jsonl', remaining)
        run_id = re.search(r'Curator run (\S+):', self.report_body()).group(1)
        self.assertIn(f'{run_id}.jsonl', remaining)


class AgentExitTests(CuratorCase):
    """After the agent exits its process group is killed; its stderr goes to a file."""

    def setUp(self):
        super().setUp()
        self.standing()

    def test_group_members_left_behind_by_a_normal_exit_are_killed(self):
        self.scenario([init(MODEL), {'spawn_child': 1}, result()])
        r = self.run_pass()
        self.assertEqual(r.code, 0, r.out + r.err)
        self.assertTrue(self.wait_dead(int((self.fakes / 'child.pid').read_text())), 'child outlived the agent')

    def test_group_members_left_behind_by_an_error_exit_are_killed(self):
        self.scenario([init(MODEL), {'spawn_child': 1}, assistant(MODEL)], exit_code=1)
        r = self.run_pass()
        self.assertEqual(r.code, 3, r.out + r.err)
        self.assertTrue(self.wait_dead(int((self.fakes / 'child.pid').read_text())))

    def test_stderr_is_written_to_the_run_stderr_file(self):
        self.scenario([init(MODEL), {'stderr': 'STDERR-MARKER one\n'}, result(), {'stderr': 'STDERR-MARKER two\n'}])
        r = self.run_pass()
        self.assertEqual(r.code, 0, r.out + r.err)
        run_id = re.search(r'Curator run (\S+):', self.report_body()).group(1)
        text = (self.state / 'runs' / f'{run_id}.stderr').read_text()
        self.assertIn('STDERR-MARKER one', text)
        self.assertIn('STDERR-MARKER two', text)
        log = (self.state / 'runs' / f'{run_id}.jsonl').read_text()
        self.assertNotIn('STDERR-MARKER', log)
        self.assertNotIn('STDERR-MARKER', r.err)


class SignalTests(CuratorCase):
    """SIGTERM and SIGINT during run behave like an exception: stop the agent, report, release, exit 3."""

    def setUp(self):
        super().setUp()
        self.standing()

    def interrupt(self, sig):
        self.scenario([{'spawn_child': 1}, init(MODEL), {'sleep': 40}, {'mark': 'survived'}])
        started = time.time()
        proc = self.start('run', '--pass', 'light')
        end = time.time() + 20
        while time.time() < end and not (self.claude_calls() and (self.fakes / 'child.pid').exists()):
            time.sleep(0.05)
        self.assertTrue(self.claude_calls(), 'agent never launched')
        time.sleep(0.7)
        proc.send_signal(sig)
        return self.finish(proc, started, timeout=60)

    def assert_stopped(self, r):
        self.assertEqual(r.code, 3, r.out + r.err)
        self.assertIn('stopped by signal', r.out)
        self.assertEqual(self.last_file()['outcome'], 'stopped by signal')
        self.assertIsNone(self.last_file()['ok_at'])
        self.assertTrue(self.wait_dead(self.claude_calls()[0]['pid']), 'agent still running')
        self.assertTrue(self.wait_dead(int((self.fakes / 'child.pid').read_text())), 'group member survived')
        self.assertFalse((self.fakes / 'survived').exists())
        self.assertIn(', stopped by signal.', self.report_body().splitlines()[0])
        self.assert_released(r, 'stopped by signal')
        self.assertLess(r.seconds, 30)

    def test_sigterm(self):
        self.assert_stopped(self.interrupt(signal.SIGTERM))

    def test_sigint(self):
        self.assert_stopped(self.interrupt(signal.SIGINT))

    def test_lock_is_free_after_a_signal(self):
        self.interrupt(signal.SIGTERM)
        import fcntl
        with open(self.state / 'curator.lock', 'a+') as f:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)


class UnexpectedExceptionTests(CuratorCase):
    """An unexpected exception after the claim is reported and released, exit 2."""

    def setUp(self):
        super().setUp()
        self.standing()

    def test_exception_after_the_claim_becomes_a_curator_error(self):
        (self.state / 'work').write_text('this is a file, not a directory')
        r = self.run_pass()
        self.assertEqual(r.code, 2, r.out + r.err)
        self.assertEqual(len(self.dibs_calls('todo:agent:claim')), 1)
        self.assertRegex(self.last_file()['outcome'], r'^curator error: \w+')
        self.assertIn('curator error: ', self.report_body().splitlines()[0])
        self.assert_released(r, 'curator error: ')
        self.assertEqual(self.claude_calls(), [])
        self.assertTrue((self.state / 'runs').is_dir())


if __name__ == '__main__':
    unittest.main()
