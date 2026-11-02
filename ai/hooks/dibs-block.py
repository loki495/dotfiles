#!/usr/bin/env python3
"""Dibs bookkeeping without tool calls.

  dibs-block.py stop       Stop (called from stop-gate.sh): apply the ```dibs block(s) in the final message.
  dibs-block.py prompt     UserPromptSubmit: claim tasks named as `dibs <id>`, report the last block's results.
  dibs-block.py heartbeat  PreToolUse: renew the claims this session made, at most every DIBS_BLOCK_BEAT_SECONDS.

Block lines (indented lines continue the previous one):
  claim <id>
  note <id>: <text>                the session's one checkpoint comment on the task (added, then edited)
  append <id> ## <Section>         text on the following indented lines goes under that heading
  done <id> sha=<sha|"none: why"> [tests="<cmd>"|tests="none: why"] [docs=a.md,b.md|docs="none: why"] :: <summary>
  atlas <subsystem>: <change>      queued in DIBS_ATLAS_HINTS for the atlas refresh job

Every action is validated and applied once (re-sent blocks are skipped); refusals block the stop once so they
can be fixed, and everything is reported on the next prompt. DIBS_BLOCK_DRY_RUN=1 reports without writing.
"""
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
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


class Refused(Exception):
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

    def save(self):
        old = os.umask(0o077)
        try:
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.state))
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
        r = cli('claim', issue, f'--agent={self.agent}', f'--pid={agent_pid()}', '--minutes=60')
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
        notes = self.state.setdefault('notes', {})
        prev = notes.get(issue)
        if prev:
            r = cli('comment', f'--comment-id={prev["id"]}', f'--expected-revision={prev["revision"]}',
                    f'--body={text.strip()}')
            if not r.get('conflict'):
                notes[issue] = {'id': prev['id'], 'revision': r.get('revision', prev['revision'] + 1)}
                return f'note {issue}: checkpoint comment {prev["id"]} updated'
        r = cli('comment', issue, f'--body={text.strip()}', f'--idempotency-key=dibs-block:{self.key}')
        notes[issue] = {'id': r['id'], 'revision': r.get('revision', 1)}
        return f'note {issue}: checkpoint comment {r["id"]} added'

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


def actions(message):
    out = []
    for block in BLOCK_RE.findall(message or ''):
        for line in block.split('\n'):
            if line.startswith((' ', '\t')) and out:
                out[-1] += '\n' + line.strip()
            elif line.strip():
                out.append(line.strip())
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


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ''
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    if not data.get('session_id'):
        return
    if mode == 'heartbeat':
        path = STATE_DIR / (re.sub(r'[^A-Za-z0-9_-]', '_', data['session_id']) + '.json')
        if not path.exists():
            return
        s = Session(data)
        if not s.state['claims'] or time.time() - s.state.get('beat', 0) < BEAT_EVERY:
            return
        s.state['beat'] = time.time()
        for issue, token in list(s.state['claims'].items()):
            try:
                cli('heartbeat', issue, f'--pid={agent_pid()}', f'--token={token}', '--minutes=60')
            except Refused:
                s.state['claims'].pop(issue)
            except (OSError, subprocess.TimeoutExpired):
                pass
        s.save()
        return
    if mode == 'prompt':
        ids = list(dict.fromkeys(PROMPT_RE.findall(data.get('prompt') or '')))
        s = Session(data)
        if not ids and not s.state['report']:
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
            return
        s, done, refused = Session(data), [], []
        for a in todo:
            ok, err = s.run(a)
            done += [ok] if ok else []
            refused += [err] if err else []
        s.state['report'] += done + refused
        s.save()
        if refused and not data.get('stop_hook_active'):
            print(json.dumps({'decision': 'block', 'reason': 'Dibs block: ' + '; '.join(refused)
                              + '. Fix the block (or use the MCP tools) and resend; applied lines are not repeated.'}))
        elif done or refused:
            print(json.dumps({'systemMessage': 'Dibs: ' + '; '.join(done + refused)}))


if __name__ == '__main__':
    main()
