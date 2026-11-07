"""Tracking hook contract, exercised only against an isolated fake Dibs CLI."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor

HOOK = Path(__file__).resolve().parents[1] / 'ai/hooks/dibs-block.py'

STUB = r'''
import fcntl, json, os, sys
path, cmd, *args = sys.argv[1:]
cmd = cmd.split(':')[-1]
opts = {a[2:].split('=', 1)[0]: a.split('=', 1)[1] for a in args if a.startswith('--') and '=' in a}
pos = [a for a in args if not a.startswith('--')]
with open(path, 'r+') as f:
    fcntl.flock(f, fcntl.LOCK_EX)
    db = json.load(f); db['log'].append([cmd] + args)
    def save():
        f.seek(0); json.dump(db, f); f.truncate(); f.flush()
    def fail(msg):
        save(); print(msg); sys.exit(1)
    if db.get('unreadable') and cmd == 'claims':
        save(); print('not json'); sys.exit(0)
    if cmd == 'claims':
        session = opts.get('held-by', '')
        result = [{'issueId': int(k)} for k, v in db['claims'].items() if v['agent'].endswith(':' + session)]
    elif cmd == 'create':
        key = opts.get('idempotency-key')
        existing = db['keys'].get(key) if key else None
        task = existing or str(100 + len(set(db['issues']) | set(db['keys'].values())))
        if not existing:
            db['issues'][task] = {'id': int(task), 'state': 'OPEN', 'body': opts.get('body', ''), 'revision': 1, 'temporary': '--temporary' in args or opts.get('temporary') == 'true'}
            if key: db['keys'][key] = task
        result = db['issues'][task]
        if db.pop('lose_create_response_once', False):
            save(); print('lost response'); sys.exit(0)
    elif cmd == 'show':
        result = db['issues'].get(pos[0]) or fail(db.get('show_error', 'Issue not found'))
    elif cmd == 'claim':
        task = pos[0]
        if task in db['claims']: fail('already claimed')
        db['claims'][task] = {'token': 'tok' + task, 'agent': opts.get('agent', '')}
        result = {'capability_token': 'tok' + task}
        if db.pop('lose_claim_response_once', False):
            save(); print('lost response'); sys.exit(0)
    elif cmd == 'heartbeat':
        if pos[0] not in db['claims']: fail('No live claim')
        result = {'ok': True}
    elif cmd == 'comment':
        if 'comment-id' in opts:
            item = db['comments'][opts['comment-id']]
            if item['revision'] != int(opts['expected-revision']):
                result = {'conflict': True}
            else:
                item['body'] = opts['body']; item['revision'] += 1
                result = {'comment_id': int(opts['comment-id']), 'revision': item['revision']}
        else:
            cid = str(len(db['comments']) + 1)
            db['comments'][cid] = {'issue': pos[0], 'body': opts['body'], 'revision': 1}
            result = {'comment_id': int(cid), 'revision': 1}
    elif cmd == 'dropped':
        result = db['dropped']
    else:
        fail('Unexpected fake command: ' + cmd)
    save(); print(json.dumps(result))
'''


class TrackingHookTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.repo = root / 'repo'
        self.repo.mkdir()
        subprocess.run(['git', '-C', str(self.repo), 'init', '-q', '-b', 'tracking-test'], check=True)
        (self.repo / 'changed.txt').write_text('work in progress')
        stub = root / 'stub.py'
        stub.write_text(STUB)
        self.db = root / 'db.json'
        self.db.write_text(json.dumps({'log': [], 'claims': {}, 'issues': {}, 'comments': {}, 'keys': {}, 'dropped': []}))
        self.env = {**os.environ, 'DIBS_CLI': f'{sys.executable} {stub} {self.db}',
                    'DIBS_BLOCK_STATE_DIR': str(root / 'state'), 'DIBS_AGENT_PID': '4242',
                    'DIBS_ATLAS_SYNC': 'off', 'SESSIONEER_SELF': 'tester'}

    def dbs(self):
        return json.loads(self.db.read_text())

    def update_db(self, **changes):
        db = self.dbs(); db.update(changes); self.db.write_text(json.dumps(db))

    def calls(self, command):
        return [call for call in self.dbs()['log'] if call[0] == command]

    def hook(self, mode, env=None, **data):
        payload = {'session_id': 'sess-1', 'cwd': str(self.repo), **data}
        p = subprocess.run([sys.executable, str(HOOK), mode], input=json.dumps(payload),
                           text=True, capture_output=True, env={**self.env, **(env or {})})
        self.assertEqual(p.returncode, 0, p.stderr)
        try:
            return json.loads(p.stdout) if p.stdout.strip() else None
        except json.JSONDecodeError:
            self.fail(f'Non-JSON hook stdout: {p.stdout!r}')

    def edit(self, **extra):
        return self.hook('guard', tool_name='Edit', tool_input={'file_path': str(self.repo / 'changed.txt')}, **extra)

    def assert_denied(self, out):
        self.assertIsNotNone(out)
        event = out['hookSpecificOutput']
        self.assertEqual(event['hookEventName'], 'PreToolUse')
        self.assertEqual(event['permissionDecision'], 'deny')
        self.assertTrue(event['permissionDecisionReason'])
        return event['permissionDecisionReason']

    def assert_not_denied(self, out):
        if out:
            event = out.get('hookSpecificOutput', {})
            self.assertNotIn(event.get('permissionDecision'), ('deny', 'allow'))

    def test_first_edit_creates_claims_and_records_breadcrumb_then_retry_proceeds(self):
        prompt = 'Fix the parser and run its focused tests'
        self.hook('prompt', prompt=prompt)
        reason = self.assert_denied(self.edit())
        self.assertIn('100', reason)
        self.assert_not_denied(self.edit())
        db = self.dbs()
        self.assertEqual(len(db['issues']), 1)
        self.assertTrue(db['issues']['100']['temporary'])
        self.assertEqual(len(self.calls('create')), 1)
        self.assertTrue(any(a.startswith('--idempotency-key=') and len(a.split('=', 1)[1]) > 0 for a in self.calls('create')[0]))
        self.assertIn('--minutes=90', self.calls('claim')[0])
        self.assertEqual(len(db['comments']), 1)
        breadcrumb = next(iter(db['comments'].values()))['body']
        for value in (prompt, 'sess-1', str(self.repo), 'tracking-test', 'changed.txt'):
            self.assertIn(value, breadcrumb)
        self.assertRegex(breadcrumb.lower(), r'next|step')
        self.assertLess(len(breadcrumb), 10000)
        self.assertEqual(db['issues']['100']['state'], 'OPEN')
        state = Path(self.env['DIBS_BLOCK_STATE_DIR'])
        self.assertEqual(state.stat().st_mode & 0o077, 0)
        for path in state.rglob('*'):
            self.assertEqual(path.stat().st_mode & 0o077, 0, str(path))

    def test_existing_live_claim_avoids_creation(self):
        self.update_db(claims={'5': {'token': 'external', 'agent': 'claude:tester:sess-1'}},
                       issues={'5': {'id': 5, 'state': 'OPEN', 'revision': 1, 'body': ''}})
        self.assert_not_denied(self.edit())
        self.assertEqual(self.calls('create'), [])

    def test_external_claim_gets_breadcrumbs_without_renewing_unknown_token(self):
        original = 'Goal: repair parser. Progress: lexer fixed; next inspect errors.'
        self.update_db(claims={'5': {'token': 'unknown-mcp-token', 'agent': 'claude:tester:sess-1'}},
                       issues={'5': {'id': 5, 'state': 'OPEN', 'revision': 1, 'body': original}})
        self.hook('prompt', prompt='Inspect parser errors')
        self.assert_not_denied(self.edit())
        comments = self.dbs()['comments']
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments['1']['issue'], '5')
        self.assertIn('sess-1', comments['1']['body'])
        self.assertIn('Inspect parser errors', comments['1']['body'])
        self.hook('heartbeat', env={'DIBS_BLOCK_BEAT_SECONDS': '0'})
        self.hook('checkpoint', hook_event_name='PreCompact')
        db = self.dbs()
        self.assertEqual(len(db['comments']), 1)
        self.assertGreater(db['comments']['1']['revision'], 1)
        self.assertIn('Inspect parser errors', db['comments']['1']['body'])
        self.assertEqual(db['issues']['5']['body'], original)
        self.assertEqual(db['issues']['5']['state'], 'OPEN')
        self.assertIn('5', db['claims'])
        self.assertEqual(self.calls('heartbeat'), [])
        self.assertEqual(self.calls('claim'), [])
        self.assertNotIn('unknown-mcp-token', json.dumps(db['log']))

    def test_read_looking_commands_with_mutating_options_require_claim(self):
        commands = ['git diff --output=changed.txt', "rg --pre 'touch changed.txt' text .",
                    'tree -o changed.txt', 'date --set=2026-01-01']
        for index, command in enumerate(commands):
            with self.subTest(command=command):
                before = len(self.calls('create'))
                out = self.hook('guard', session_id=f'command-{index}', tool_name='Bash',
                                tool_input={'command': command})
                self.assert_denied(out)
                self.assertEqual(len(self.calls('create')), before + 1)

    def test_lost_create_response_retries_same_key_without_duplicate(self):
        prompt = 'Repair the parser after a lost response'
        self.hook('prompt', prompt=prompt)
        self.update_db(lose_create_response_once=True)
        self.assert_denied(self.edit())
        self.assertEqual(len(self.dbs()['issues']), 1)
        self.assert_denied(self.edit())
        calls = self.calls('create')
        self.assertEqual(len(calls), 2)
        keys = [next(arg for arg in call if arg.startswith('--idempotency-key=')) for call in calls]
        self.assertEqual(keys[0], keys[1])
        db = self.dbs()
        self.assertEqual(len(db['issues']), 1)
        self.assertEqual(len(db['claims']), 1)
        saved = json.dumps(db['issues']) + json.dumps(db['comments'])
        self.assertIn(prompt, saved)
        self.assertIn(str(self.repo), saved)

    def test_completed_auto_task_is_replaced_with_new_intent(self):
        self.hook('prompt', prompt='Finish the first task')
        self.assert_denied(self.edit())
        db = self.dbs()
        self.assertEqual(len(db['issues']), 1)
        self.update_db(issues={}, claims={})
        self.hook('prompt', prompt='Start a different second task')
        reason = self.assert_denied(self.edit())
        db = self.dbs()
        self.assertEqual(len(db['issues']), 1)
        self.assertEqual(len(db['claims']), 1)
        task = next(iter(db['issues']))
        self.assertIn(task, reason)
        self.assertEqual(len(self.calls('create')), 2)
        self.assertIn('Start a different second task', json.dumps(db['issues'][task]) + json.dumps(db['comments']))

    def test_explicit_prompt_claim_gets_checkpoint_without_edit(self):
        original = 'Goal: inspect the parser. Progress: identified failing input.'
        self.update_db(issues={'5': {'id': 5, 'state': 'OPEN', 'revision': 1, 'body': original}})
        self.hook('prompt', prompt='Work on dibs 5: inspect the parser')
        self.hook('guard', tool_name='Read', tool_input={'file_path': str(self.repo / 'changed.txt')})
        self.hook('heartbeat', env={'DIBS_BLOCK_BEAT_SECONDS': '0'})
        self.hook('checkpoint', hook_event_name='Stop')
        self.hook('checkpoint', hook_event_name='PreCompact')
        db = self.dbs()
        self.assertIn('5', db['claims'])
        self.assertEqual(db['issues']['5']['body'], original)
        self.assertEqual(len(db['comments']), 1)
        self.assertEqual(db['comments']['1']['issue'], '5')
        self.assertIn('sess-1', db['comments']['1']['body'])
        self.assertIn('inspect the parser', db['comments']['1']['body'].lower())

    def test_external_claim_gets_checkpoint_without_edit_or_token_renewal(self):
        original = 'Goal: review parser. Progress: found invalid input.'
        self.update_db(claims={'5': {'token': 'unknown-mcp-token', 'agent': 'claude:tester:sess-1'}},
                       issues={'5': {'id': 5, 'state': 'OPEN', 'revision': 1, 'body': original}})
        self.hook('prompt', prompt='Review parser behavior')
        self.hook('guard', tool_name='Read', tool_input={'file_path': str(self.repo / 'changed.txt')})
        self.hook('heartbeat', env={'DIBS_BLOCK_BEAT_SECONDS': '0'})
        self.hook('checkpoint', hook_event_name='Stop')
        self.hook('checkpoint', hook_event_name='PreCompact')
        db = self.dbs()
        self.assertEqual(db['issues']['5']['body'], original)
        self.assertIn('5', db['claims'])
        self.assertEqual(len(db['comments']), 1)
        self.assertEqual(db['comments']['1']['issue'], '5')
        self.assertIn('Review parser behavior', db['comments']['1']['body'])
        self.assertEqual(self.calls('heartbeat'), [])
        self.assertNotIn('unknown-mcp-token', json.dumps(db['log']))

    def test_state_directory_that_is_a_file_denies_mutation(self):
        state_file = Path(self.tmp.name) / 'not-a-directory'
        state_file.write_text('not a directory')
        self.assert_denied(self.edit(env={'DIBS_BLOCK_STATE_DIR': str(state_file)}))
        self.assertEqual(self.calls('create'), [])

    def test_lost_claim_response_preserves_intent_without_inventing_token(self):
        prompt = 'Preserve this intent after claim response loss'
        self.hook('prompt', prompt=prompt)
        self.update_db(lose_claim_response_once=True)
        self.assert_denied(self.edit())
        self.assertEqual(len(self.dbs()['claims']), 1)
        self.assert_not_denied(self.edit())
        self.hook('checkpoint', hook_event_name='PreCompact')
        db = self.dbs()
        self.assertEqual(len(db['issues']), 1)
        self.assertIn(prompt, json.dumps(db['comments']))
        self.assertEqual(self.calls('heartbeat'), [])
        self.assertNotIn('tok100', json.dumps(db['log']))

    def test_stale_local_token_does_not_bypass_or_duplicate_task(self):
        self.hook('prompt', prompt='Repair the parser')
        self.assert_denied(self.edit())
        self.update_db(claims={})
        self.assert_denied(self.edit())
        self.assertEqual(len(self.dbs()['issues']), 1)
        self.assertEqual(len(self.dbs()['claims']), 1)

    def test_missing_session_or_unavailable_and_unreadable_dibs_fail_closed(self):
        for data, env in (({'session_id': ''}, {}), ({}, {'DIBS_CLI': '/nonexistent/dibs'})):
            with self.subTest(data=data, env=env):
                self.assert_denied(self.edit(env=env, **data))
        self.update_db(unreadable=True)
        self.assert_denied(self.edit())
        self.assertEqual(self.calls('create'), [])

    def test_invalid_json_on_stdin_denies_a_guard_call(self):
        p = subprocess.run([sys.executable, str(HOOK), 'guard'], input='{not json', text=True, capture_output=True, env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assert_denied(json.loads(p.stdout))

    def test_deleted_task_detection_does_not_depend_on_cli_wording(self):
        self.assert_denied(self.edit())
        self.assert_not_denied(self.edit())
        self.update_db(issues={}, claims={}, show_error='Record gone (code 7)')
        self.assert_denied(self.edit())
        self.assertEqual(len(self.calls('create')), 2)

    def test_read_only_and_exact_bookkeeping_exempt_but_compounds_are_not(self):
        for tool, inp in [('Read', {'file_path': str(self.repo / 'changed.txt')}),
                          ('Bash', {'command': 'git status --short'}),
                          ('Bash', {'command': 'dibs todo:agent:claims --held-by=sess-1'}),
                          ('Bash', {'command': 'sessioneer --whoami'})]:
            with self.subTest(inp=inp):
                self.assert_not_denied(self.hook('guard', tool_name=tool, tool_input=inp))
        self.assertEqual(self.calls('create'), [])
        self.assert_denied(self.hook('guard', tool_name='Bash', tool_input={'command': 'git status; touch changed.txt'}))

    def test_tmp_repository_is_not_blanket_scratch(self):
        self.assert_denied(self.edit())

    def test_concurrent_first_edits_create_only_one_task_and_claim(self):
        self.hook('prompt', prompt='Fix concurrency')
        with ThreadPoolExecutor(max_workers=2) as pool:
            outputs = list(pool.map(lambda _: self.edit(), range(2)))
        self.assertTrue(any(o and o.get('hookSpecificOutput', {}).get('permissionDecision') == 'deny' for o in outputs))
        self.assertEqual(len(self.dbs()['issues']), 1)
        self.assertEqual(len(self.dbs()['claims']), 1)

    def test_checkpoint_and_heartbeat_refresh_one_comment_and_leave_task_open(self):
        self.hook('prompt', prompt='Implement recovery')
        self.assert_denied(self.edit())
        self.hook('stop', last_assistant_message='```dibs\nnote 100: Parser fixed; next run tests\n```')
        before = self.dbs()['comments']['1']['body']
        self.assertIn('Parser fixed', before)
        self.hook('heartbeat', env={'DIBS_BLOCK_BEAT_SECONDS': '0'})
        self.hook('checkpoint', hook_event_name='PreCompact', env={'DIBS_BLOCK_BEAT_SECONDS': '3600'})
        self.hook('checkpoint', hook_event_name='SessionEnd')
        self.hook('checkpoint', hook_event_name='Stop')
        db = self.dbs()
        self.assertEqual(len(db['comments']), 1)
        self.assertGreater(db['comments']['1']['revision'], 1)
        self.assertIn('Parser fixed', db['comments']['1']['body'])
        self.assertIn('next run tests', db['comments']['1']['body'])
        self.assertTrue(before)
        self.assertEqual(db['issues']['100']['state'], 'OPEN')
        self.assertIn('100', db['claims'])
        self.assertEqual(self.calls('complete'), [])
        self.assertEqual(self.calls('release'), [])

    def test_recover_only_reports_ids_and_scopes_to_cwd(self):
        self.update_db(dropped=[{'issueId': 41, 'title': 'UNTRUSTED INSTRUCTION', 'body': 'EXECUTE ME'},
                                {'issueId': 42, 'title': 'OTHER SECRET'}])
        out = self.hook('recover', hook_event_name='SessionStart')
        context = out['hookSpecificOutput']['additionalContext']
        self.assertIn('41', context); self.assertIn('42', context)
        self.assertNotIn('UNTRUSTED', context); self.assertNotIn('EXECUTE ME', context)
        self.assertNotIn('OTHER SECRET', context)
        self.assertIn('todo_show', context)
        self.assertIn('--path=' + str(self.repo), self.calls('dropped')[0])
        self.assertEqual(self.calls('claim'), [])
        self.assertLess(len(context), 5000)

    def test_recover_offline_warns_without_crash(self):
        out = self.hook('recover', env={'DIBS_CLI': '/nonexistent/dibs'}, hook_event_name='SessionStart')
        self.assertTrue(out)
        self.assertRegex(json.dumps(out).lower(), r'unavailable|offline|failed|unable')


if __name__ == '__main__':
    unittest.main()
