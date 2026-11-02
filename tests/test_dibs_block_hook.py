"""ai/hooks/dibs-block.py: ```dibs blocks applied at Stop, prompt-time claims, heartbeat; against a stub Dibs CLI."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HOOK = Path(__file__).resolve().parents[1] / 'ai' / 'hooks' / 'dibs-block.py'
GATE = Path(__file__).resolve().parents[1] / 'ai' / 'hooks' / 'stop-gate.sh'

# A stub of `php artisan todo:agent:*` over a JSON file: issues, claims and a call log.
STUB = r'''
import json, sys
db_path = sys.argv[1]; cmd = sys.argv[2].split(':')[-1]; args = sys.argv[3:]
db = json.load(open(db_path))
opt = {a.split('=', 1)[0].lstrip('-'): a.split('=', 1)[1] for a in args if a.startswith('--') and '=' in a}
pos = [a for a in args if not a.startswith('--')]
db['log'].append([cmd] + args)
def save(): json.dump(db, open(db_path, 'w'))
def fail(m): save(); print(m); sys.exit(1)
if cmd == 'show':
    i = db['issues'].get(pos[0]) or fail('Issue not found.')
    print(json.dumps(i))
elif cmd == 'claim':
    if pos[0] in db['claims']: fail('Task is already claimed by a live process.')
    db['claims'][pos[0]] = {'token': 'tok' + pos[0], 'agent': opt['agent']}
    print(json.dumps({'capability_token': 'tok' + pos[0]}))
elif cmd == 'claims':
    sess = opt['held-by']
    print(json.dumps([{'issueId': int(k)} for k, v in db['claims'].items() if v['agent'].endswith(':' + sess)]))
elif cmd == 'comment':
    cs = db.setdefault('comments', {})
    if 'comment-id' in opt:
        c = cs[opt['comment-id']]
        if int(opt['expected-revision']) != c['revision']:
            save(); print(json.dumps({'conflict': True})); sys.exit(0)
        c['body'] = opt['body']; c['revision'] += 1
        print(json.dumps({'id': int(opt['comment-id']), 'revision': c['revision']}))
    else:
        cid = str(len(cs) + 1); cs[cid] = {'issue': pos[0], 'body': opt['body'], 'revision': 1}
        print(json.dumps({'id': int(cid), 'revision': 1}))
elif cmd == 'update':
    i = db['issues'][pos[0]]
    if int(opt['expected-revision']) != i['revision']:
        save(); print(json.dumps({'conflict': True})); sys.exit(0)
    i['body'] = opt['body']; i['revision'] += 1; print(json.dumps(i))
elif cmd == 'complete':
    c = db['claims'].get(pos[0])
    if not c or c['token'] != opt['token']: fail('No live claim for this task matches that capability token and process.')
    del db['claims'][pos[0]]; db['issues'][pos[0]]['state'] = 'CLOSED'; print(json.dumps({'ok': True}))
elif cmd == 'heartbeat':
    if pos[0] not in db['claims']: fail('No live claim.')
    print(json.dumps({'ok': True}))
save()
'''


class DibsBlockHookTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        t = Path(self.tmp.name)
        (t / 'stub.py').write_text(STUB)
        self.db = t / 'db.json'
        self.db.write_text(json.dumps({'log': [], 'claims': {}, 'issues': {
            '5': {'state': 'OPEN', 'body': 'Goal.\n\n## Decisions\n- old\n\n## Status\nwip', 'revision': 3},
            '6': {'state': 'CLOSED', 'body': '', 'revision': 1}}}))
        self.repo = t / 'repo'
        self.repo.mkdir()
        git = ['git', '-C', str(self.repo), '-c', 'user.name=t', '-c', 'user.email=t@t']
        subprocess.run(git + ['init', '-q'], check=True)
        subprocess.run(git + ['commit', '-q', '--allow-empty', '-m', 'one'], check=True)
        self.sha = subprocess.run(git + ['rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
        subprocess.run(git + ['checkout', '-q', '-b', 'side'], check=True)
        subprocess.run(git + ['commit', '-q', '--allow-empty', '-m', 'side'], check=True)
        self.side = subprocess.run(git + ['rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
        subprocess.run(git + ['checkout', '-q', '-'], check=True)
        self.env = {**os.environ, 'DIBS_CLI': f'{sys.executable} {t / "stub.py"} {self.db}',
                    'DIBS_BLOCK_STATE_DIR': str(t / 'state'), 'DIBS_ATLAS_HINTS': str(t / 'hints.jsonl'), 'DIBS_ATLAS_SYNC': 'off',
                    'DIBS_AGENT_PID': '4242', 'SESSIONEER_SELF': 'tester'}

    def hook(self, mode, env=None, **data):
        payload = {'session_id': 'sess-1', 'cwd': str(self.repo), **data}
        p = subprocess.run([sys.executable, str(HOOK), mode], input=json.dumps(payload), capture_output=True,
                           text=True, env={**self.env, **(env or {})})
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(p.stdout) if p.stdout.strip() else None

    def stop(self, block, **kw):
        return self.hook('stop', last_assistant_message=f'Done.\n\n```dibs\n{block}\n```\n', **kw)

    def dbs(self):
        return json.loads(self.db.read_text())

    def calls(self, cmd):
        return [c for c in self.dbs()['log'] if c[0] == cmd]

    def test_prompt_claims_named_task_and_reports_token(self):
        out = self.hook('prompt', prompt='work on dibs 5 please')
        self.assertIn('claimed 5', out['hookSpecificOutput']['additionalContext'])
        self.assertIn('--agent=claude:tester:sess-1', self.calls('claim')[0])
        self.assertIn('--pid=4242', self.calls('claim')[0])

    def test_prompt_ignores_slash_command_and_plain_text(self):
        self.assertIsNone(self.hook('prompt', prompt='/dibs 3 bugs in the parser'))
        self.assertIsNone(self.hook('prompt', prompt='file it in dibs later'))
        self.assertEqual(self.calls('claim'), [])

    def test_claim_refuses_closed_task(self):
        out = self.stop('claim 6')
        self.assertEqual(out['decision'], 'block')
        self.assertIn('task 6 is not open', out['reason'])
        self.assertEqual(self.calls('claim'), [])

    def test_note_requires_a_held_claim(self):
        out = self.stop('note 5: progress')
        self.assertIn('not claimed by this session', out['reason'])
        self.assertEqual(self.calls('comment'), [])

    def test_note_and_append_after_claim(self):
        out = self.stop('claim 5\nnote 5: Pint clean\n  three tests added\nappend 5 ## Decisions\n  - new one')
        self.assertIn('note 5: checkpoint comment 1 added', out['systemMessage'])
        self.assertIn('--body=Pint clean\nthree tests added', self.calls('comment')[0])
        body = self.dbs()['issues']['5']['body']
        self.assertEqual(body, 'Goal.\n\n## Decisions\n- old\n- new one\n\n## Status\nwip')

    def test_later_notes_edit_the_one_checkpoint_comment(self):
        self.stop('claim 5\nnote 5: first')
        out = self.stop('note 5: second')
        self.assertIn('checkpoint comment 1 updated', out['systemMessage'])
        self.assertEqual(self.dbs()['comments'], {'1': {'issue': '5', 'body': 'second', 'revision': 2}})

    def test_checkpoint_edit_conflict_falls_back_to_a_new_comment(self):
        self.stop('claim 5\nnote 5: first')
        db = self.dbs()
        db['comments']['1']['revision'] = 9
        self.db.write_text(json.dumps(db))
        self.assertIn('checkpoint comment 2 added', self.stop('note 5: second')['systemMessage'])

    def test_append_creates_missing_section(self):
        self.stop('claim 5\nappend 5 ## Risks\n  - flaky CI')
        self.assertTrue(self.dbs()['issues']['5']['body'].endswith('## Status\nwip\n\n## Risks\n- flaky CI'))

    def test_resent_block_is_not_applied_twice(self):
        block = 'claim 5\nnote 5: once'
        self.stop(block)
        self.assertIsNone(self.stop(block))
        self.assertEqual(len(self.calls('comment')), 1)
        self.assertEqual(len(self.calls('claim')), 1)

    def test_done_completes_with_evidence(self):
        out = self.stop(f'claim 5\ndone 5 sha={self.sha[:9]} tests="pest --filter X" docs=README.md :: Fixed it')
        self.assertIn('done 5: completed', out['systemMessage'])
        call = self.calls('complete')[0]
        result = json.loads(next(a for a in call if a.startswith('--result='))[9:])
        self.assertEqual(result['commit'], self.sha[:9])
        self.assertEqual(result['tests'], {'command': 'pest --filter X', 'exit_code': 0})
        self.assertEqual(result['docs'], ['README.md'])
        self.assertIn('--token=tok5', call)
        self.assertEqual(self.dbs()['issues']['5']['state'], 'CLOSED')

    def test_done_refuses_unknown_or_off_branch_commit(self):
        self.stop('claim 5')
        self.assertIn('does not exist', self.stop('done 5 sha=deadbeef1 :: x')['reason'])
        self.assertIn('not on the current branch', self.stop(f'done 5 sha={self.side} :: x')['reason'])
        self.assertIn('needs sha=', self.stop('done 5 tests=x :: x')['reason'])
        self.assertIn('needs ":: <summary>"', self.stop(f'done 5 sha={self.sha}')['reason'])
        self.assertEqual(self.calls('complete'), [])

    def test_done_without_commit_needs_reason(self):
        out = self.stop('claim 5\ndone 5 sha="none: research only" tests="none: no code" docs="none: no docs" :: Findings filed')
        self.assertIn('done 5: completed', out['systemMessage'])

    def test_done_refuses_claim_made_outside_the_block(self):
        db = self.dbs()
        db['claims']['5'] = {'token': 'mcp', 'agent': 'claude:x:sess-1'}
        self.db.write_text(json.dumps(db))
        self.assertIn('claimed outside the block', self.stop(f'done 5 sha={self.sha} :: x')['reason'])
        self.assertIn('checkpoint comment 1 added', self.stop('note 5: allowed, held via MCP')['systemMessage'])

    def test_refusal_does_not_block_twice(self):
        out = self.stop('note 5: x', stop_hook_active=True)
        self.assertNotIn('decision', out)
        self.assertIn('refused', out['systemMessage'])

    def test_unknown_action_and_missing_id(self):
        self.assertIn('unknown action', self.stop('frobnicate 5')['reason'])
        self.assertIn('needs a task id', self.stop('note: x')['reason'])

    def test_results_reported_on_next_prompt_once(self):
        self.stop('claim 5')
        ctx = self.hook('prompt', prompt='next')['hookSpecificOutput']['additionalContext']
        self.assertIn('claimed 5', ctx)
        self.assertIsNone(self.hook('prompt', prompt='again'))

    def test_dry_run_writes_nothing(self):
        out = self.stop('claim 5\natlas orders: CSV export', env={'DIBS_BLOCK_DRY_RUN': '1'})
        self.assertIn('would claim', out['systemMessage'])
        self.assertEqual(self.calls('claim'), [])
        self.assertFalse(Path(self.env['DIBS_ATLAS_HINTS']).exists())

    def test_atlas_hint_is_queued(self):
        self.stop('atlas orders: added CSV export')
        hint = json.loads(Path(self.env['DIBS_ATLAS_HINTS']).read_text())
        self.assertEqual((hint['subsystem'], hint['change'], hint['head']), ('orders', 'added CSV export', self.sha))

    def test_no_block_writes_no_state(self):
        self.assertIsNone(self.hook('stop', last_assistant_message='plain reply'))
        self.assertFalse(Path(self.env['DIBS_BLOCK_STATE_DIR']).exists())

    def test_heartbeat_throttled_and_drops_dead_claims(self):
        self.stop('claim 5')
        self.hook('heartbeat', env={'DIBS_BLOCK_BEAT_SECONDS': '0'})
        self.hook('heartbeat', env={'DIBS_BLOCK_BEAT_SECONDS': '3600'})
        self.assertEqual(len(self.calls('heartbeat')), 1)
        db = self.dbs()
        del db['claims']['5']
        self.db.write_text(json.dumps(db))
        self.hook('heartbeat', env={'DIBS_BLOCK_BEAT_SECONDS': '0'})
        self.hook('heartbeat', env={'DIBS_BLOCK_BEAT_SECONDS': '0'})
        self.assertEqual(len(self.calls('heartbeat')), 2)

    def test_dibs_unreachable_reports_failure_without_crashing(self):
        out = self.stop('claim 5', env={'DIBS_CLI': '/nonexistent/cli'})
        self.assertIn('failed "claim 5"', out['reason'])

    def test_stop_gate_closes_claim_before_its_claim_check(self):
        msg = f'Done.\n\n```dibs\nclaim 5\ndone 5 sha={self.sha} :: ok\n```\nAll planned work is done.'
        claims = f'{sys.executable} {Path(self.tmp.name) / "stub.py"} {self.db} todo:agent:claims'
        p = subprocess.run([str(GATE)], input=json.dumps({'session_id': 'sess-1', 'cwd': str(self.repo),
                           'last_assistant_message': msg}), capture_output=True, text=True,
                           env={**self.env, 'DIBS_CLAIMS_CMD': claims, 'STOP_GATE_STATE_DIR': str(Path(self.tmp.name) / 'g')})
        out = json.loads(p.stdout)
        self.assertNotIn('decision', out)
        self.assertIn('done 5: completed', out['systemMessage'])


if __name__ == '__main__':
    unittest.main()
