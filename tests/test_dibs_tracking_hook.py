"""Tracking hook contract (claim-or-work-line guard + breadcrumbs), exercised only against an isolated fake Dibs CLI."""
import json
import os
import re
import time
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
        if os.environ.get('PROBE'):
            db['probe'] = open(os.environ['PROBE']).read() if os.path.exists(os.environ['PROBE']) else None
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
        self.tmp = tempfile.TemporaryDirectory(dir='/var/tmp')  # outside /tmp: /tmp edits are exempt
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
                    'DIBS_ATLAS_SYNC': 'off', 'SESSIONEER_SELF': 'tester',
                    'XDG_RUNTIME_DIR': str(root / 'xdg')}
        (root / 'xdg').mkdir()
        self.state = root / 'state'

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

    def bash(self, command, session='b', **extra):
        return self.hook('guard', session_id=session, tool_name='Bash', tool_input={'command': command}, **extra)

    def assert_never_denied(self, out):
        if out:
            self.assertNotEqual(out.get('hookSpecificOutput', {}).get('permissionDecision'), 'deny')

    def assert_denied(self, out):
        self.assertIsNotNone(out)
        event = out['hookSpecificOutput']
        self.assertEqual((event['hookEventName'], event['permissionDecision']), ('PreToolUse', 'deny'))
        return event['permissionDecisionReason']

    def mutate(self, tool='Edit', session='sess-1', env=None, **inp):
        inp = inp or {'file_path': str(self.repo / 'changed.txt')}
        return self.hook('guard', session_id=session, tool_name=tool, tool_input=inp, env=env)

    def auto_edit(self, tool='Edit', session='sess-1', env=None, **inp):
        """Contract 2: two denials without a claim, then the third mutating call opens the temporary task and is allowed."""
        for _ in range(2):
            self.assert_denied(self.mutate(tool, session, env, **inp))
        return self.mutate(tool, session, env, **inp)

    def assert_allowed(self, out, task=None):
        self.assertIsNotNone(out)
        event = out['hookSpecificOutput']
        self.assertEqual(event['hookEventName'], 'PreToolUse')
        self.assertEqual(event['permissionDecision'], 'allow')
        if task:
            self.assertIn(task, event['additionalContext'])
        self.assertIn('breadcrumb', event['additionalContext'].lower())
        return event['additionalContext']

    def state_file(self, session='sess-1'):
        return self.state / f'{session}.json'

    def breadcrumb(self, session='sess-1'):
        return json.loads(self.state_file(session).read_text())['breadcrumb']

    def settle(self, out):
        """Not denied and not allowed: nothing printed."""
        self.assertIsNone(out)

    # --- contract 2: a change without a claim or work line is denied twice, then auto-tracked with a warning ---

    def test_first_edit_without_claim_or_work_line_is_denied_and_creates_nothing(self):
        self.hook('prompt', prompt='Fix the parser and run its focused tests')
        reason = self.assert_denied(self.edit())
        self.assertIn('[work', reason)
        self.assertEqual(self.calls('create'), [])
        self.assertEqual(self.calls('claim'), [])
        self.assertEqual(self.dbs()['claims'], {})

    def test_third_edit_after_two_denials_allows_creates_claims_and_records_breadcrumb(self):
        prompt = 'Fix the parser and run its focused tests'
        self.hook('prompt', prompt=prompt)
        out = self.auto_edit()
        self.assert_allowed(out, '100')
        self.assertIn('Dibs', out['systemMessage'])
        self.assertEqual(self.calls('create')[0][0], 'create')
        self.assertTrue(any(a.startswith('--title=Auto-tracked:') or 'Auto-tracked:' in a for a in self.calls('create')[0]))
        db = self.dbs()
        self.assertEqual(len(db['issues']), 1)
        self.assertTrue(db['issues']['100']['temporary'])
        self.assertEqual(len(self.calls('create')), 1)
        self.assertEqual(len(self.calls('claim')), 1)
        self.assertIn('100', db['claims'])
        b = self.breadcrumb()
        self.assertEqual((b['prompt'], b['cwd'], b['branch'], b['pid']), (prompt, str(self.repo), 'tracking-test', 4242))
        self.assertIsInstance(b['ts'], int)
        self.assertLess(abs(b['ts'] - time.time()), 60)

    def test_breadcrumb_without_recorded_prompt(self):
        self.assert_allowed(self.auto_edit())
        self.assertEqual(self.breadcrumb()['prompt'], '(no prompt recorded)')

    def test_breadcrumb_is_written_before_any_dibs_call(self):
        self.hook('prompt', prompt='Probe ordering')
        self.assert_allowed(self.auto_edit(env={'PROBE': str(self.state_file())}))
        probe = self.dbs()['probe']
        self.assertIsNotNone(probe)
        self.assertIn('Probe ordering', probe)

    def test_second_mutating_call_in_session_does_not_create_again(self):
        self.assert_allowed(self.auto_edit())
        self.assert_never_denied(self.edit())
        self.bash('touch f', session='sess-1')
        self.assertEqual(len(self.calls('create')), 1)

    def test_existing_live_claim_avoids_creation_and_output(self):
        self.update_db(claims={'5': {'token': 'external', 'agent': 'claude:tester:sess-1'}},
                       issues={'5': {'id': 5, 'state': 'OPEN', 'revision': 1, 'body': ''}})
        self.settle(self.edit())
        self.assertEqual(self.calls('create'), [])

    def test_external_claim_gets_breadcrumbs_without_renewing_unknown_token(self):
        original = 'Goal: repair parser. Progress: lexer fixed; next inspect errors.'
        self.update_db(claims={'5': {'token': 'unknown-mcp-token', 'agent': 'claude:tester:sess-1'}},
                       issues={'5': {'id': 5, 'state': 'OPEN', 'revision': 1, 'body': original}})
        self.hook('prompt', prompt='Inspect parser errors')
        self.settle(self.edit())
        self.hook('heartbeat', env={'DIBS_BLOCK_BEAT_SECONDS': '0'})
        self.hook('checkpoint', hook_event_name='PreCompact')
        db = self.dbs()
        self.assertEqual(len(db['comments']), 1)
        self.assertEqual(db['comments']['1']['issue'], '5')
        self.assertIn('Inspect parser errors', db['comments']['1']['body'])
        self.assertEqual(db['issues']['5']['body'], original)
        self.assertEqual(self.calls('heartbeat'), [])
        self.assertEqual(self.calls('claim'), [])
        self.assertNotIn('unknown-mcp-token', json.dumps(db['log']))

    def test_lost_create_response_retries_same_key_without_duplicate(self):
        self.hook('prompt', prompt='Repair the parser after a lost response')
        self.update_db(lose_create_response_once=True)
        for _ in range(2):
            self.assert_denied(self.edit())
        self.assert_never_denied(self.edit())
        self.assertEqual(len(self.dbs()['issues']), 1)
        self.assert_never_denied(self.edit())
        calls = self.calls('create')
        self.assertEqual(len(calls), 2)
        keys = [next(a for a in c if a.startswith('--idempotency-key=')) for c in calls]
        self.assertEqual(keys[0], keys[1])
        self.assertEqual(len(self.dbs()['issues']), 1)
        self.assertEqual(len(self.dbs()['claims']), 1)

    def test_completed_auto_task_is_replaced(self):
        self.hook('prompt', prompt='Finish the first task')
        self.assert_allowed(self.auto_edit(), '100')
        self.update_db(issues={}, claims={})
        self.hook('prompt', prompt='Start a different second task')
        self.assert_allowed(self.auto_edit())
        self.assertEqual(len(self.dbs()['claims']), 1)
        self.assertEqual(len(self.calls('create')), 2)

    def test_stale_local_token_does_not_bypass_or_duplicate_task(self):
        self.assert_allowed(self.auto_edit())
        self.update_db(claims={})
        self.assert_never_denied(self.auto_edit())
        self.assertEqual(len(self.dbs()['issues']), 1)
        self.assertEqual(len(self.dbs()['claims']), 1)

    def test_deleted_task_detection_does_not_depend_on_cli_wording(self):
        self.assert_allowed(self.auto_edit())
        self.update_db(issues={}, claims={}, show_error='Record gone (code 7)')
        self.assert_allowed(self.auto_edit())
        self.assertEqual(len(self.calls('create')), 2)

    def test_concurrent_first_edits_create_only_one_task_and_claim(self):
        self.hook('prompt', prompt='Fix concurrency')
        for _ in range(2):
            self.assert_denied(self.edit())
        with ThreadPoolExecutor(max_workers=2) as pool:
            outputs = list(pool.map(lambda _: self.edit(), range(2)))
        for out in outputs:
            self.assert_never_denied(out)
        self.assertEqual(len(self.dbs()['issues']), 1)
        self.assertEqual(len(self.dbs()['claims']), 1)

    def test_checkpoint_and_heartbeat_refresh_one_comment_and_leave_task_open(self):
        self.hook('prompt', prompt='Implement recovery')
        self.assert_allowed(self.auto_edit())
        self.hook('stop', last_assistant_message='```dibs\nnote 100: Parser fixed; next run tests\n```')
        self.assertIn('Parser fixed', self.dbs()['comments']['1']['body'])
        self.hook('heartbeat', env={'DIBS_BLOCK_BEAT_SECONDS': '0'})
        self.hook('checkpoint', hook_event_name='PreCompact', env={'DIBS_BLOCK_BEAT_SECONDS': '3600'})
        self.hook('checkpoint', hook_event_name='SessionEnd')
        self.hook('checkpoint', hook_event_name='Stop')
        db = self.dbs()
        self.assertEqual(len(db['comments']), 1)
        self.assertGreater(db['comments']['1']['revision'], 1)
        self.assertIn('next run tests', db['comments']['1']['body'])
        self.assertEqual(db['issues']['100']['state'], 'OPEN')
        self.assertIn('100', db['claims'])
        self.assertEqual(self.calls('complete'), [])

    def test_explicit_prompt_claim_gets_checkpoint_without_edit(self):
        original = 'Goal: inspect the parser. Progress: identified failing input.'
        self.update_db(issues={'5': {'id': 5, 'state': 'OPEN', 'revision': 1, 'body': original}})
        self.hook('prompt', prompt='Work on dibs 5: inspect the parser')
        self.hook('guard', tool_name='Read', tool_input={'file_path': str(self.repo / 'changed.txt')})
        self.hook('heartbeat', env={'DIBS_BLOCK_BEAT_SECONDS': '0'})
        self.hook('checkpoint', hook_event_name='Stop')
        db = self.dbs()
        self.assertIn('5', db['claims'])
        self.assertEqual(db['issues']['5']['body'], original)
        self.assertEqual(len(db['comments']), 1)
        self.assertIn('inspect the parser', db['comments']['1']['body'].lower())

    # --- contract 2: Dibs down, bad input or unusable state degrade to a warning, never a denial ---

    def test_never_denies_on_missing_session_invalid_json_or_dibs_down(self):
        for data, env in (({'session_id': ''}, {}), ({}, {'DIBS_CLI': '/nonexistent/dibs'})):
            with self.subTest(data=data, env=env):
                self.assert_never_denied(self.edit(env=env, **data))
        p = subprocess.run([sys.executable, str(HOOK), 'guard'], input='{not json', text=True, capture_output=True, env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertNotIn('"deny"', p.stdout)

    def test_state_directory_that_is_a_file_does_not_deny(self):
        state_file = Path(self.tmp.name) / 'not-a-directory'
        state_file.write_text('not a directory')
        self.assert_never_denied(self.edit(env={'DIBS_BLOCK_STATE_DIR': str(state_file)}))

    def test_unreadable_claims_output_does_not_deny(self):
        self.update_db(unreadable=True)
        self.assert_never_denied(self.edit())

    def test_dibs_down_allows_warns_and_keeps_breadcrumb(self):
        failing = Path(self.tmp.name) / 'fail.py'
        failing.write_text('import sys\nprint("boom")\nsys.exit(1)\n')
        for index, cli in enumerate((f'{sys.executable} {failing}', '/nonexistent/dibs')):
            with self.subTest(cli=cli):
                session = f'down-{index}'
                self.hook('prompt', session_id=session, prompt=f'Offline work {index}')
                out = self.hook('guard', session_id=session, tool_name='Edit', env={'DIBS_CLI': cli},
                                tool_input={'file_path': str(self.repo / 'changed.txt')})
                self.assertIsNotNone(out)
                self.assertNotEqual(out.get('hookSpecificOutput', {}).get('permissionDecision'), 'deny')
                self.assertIn('Dibs', out['systemMessage'])
                b = self.breadcrumb(session)
                self.assertEqual(b['prompt'], f'Offline work {index}')
                self.assertEqual(b['cwd'], str(self.repo))
                self.assertNotIn('auto', json.loads(self.state_file(session).read_text()))
        self.assertEqual(self.calls('create'), [])

    # --- contract 2: subagents ---

    def test_subagent_calls_print_nothing_call_nothing_write_nothing(self):
        for tool, inp in (('Edit', {'file_path': str(self.repo / 'changed.txt')}), ('Bash', {'command': 'touch f'})):
            with self.subTest(tool=tool):
                self.settle(self.hook('guard', tool_name=tool, tool_input=inp, agent_id='agent-7'))
        self.assertEqual(self.dbs()['log'], [])
        self.assertFalse(self.state.exists())

    # --- contract 3 and 7: tool scope ---

    def test_non_mutating_tools_and_scratch_paths_are_silent(self):
        xdg = self.env['XDG_RUNTIME_DIR']
        for tool, inp in (('Read', {'file_path': str(self.repo / 'changed.txt')}), ('Grep', {'pattern': 'x'}),
                          ('Glob', {'pattern': '*'}), ('WebFetch', {'url': 'https://example.test/'}),
                          ('Write', {'file_path': '/tmp/scratch.txt'}), ('Edit', {'file_path': '/tmp/a/b.txt'}),
                          ('MultiEdit', {'file_path': xdg + '/x'}), ('NotebookEdit', {'file_path': xdg + '/n.ipynb'})):
            with self.subTest(tool=tool, inp=inp):
                self.settle(self.hook('guard', tool_name=tool, tool_input=inp))
        self.assertEqual(self.calls('create'), [])

    def test_all_edit_tools_outside_tmp_are_mutating(self):
        for index, tool in enumerate(('Edit', 'Write', 'MultiEdit', 'NotebookEdit')):
            with self.subTest(tool=tool):
                self.assert_denied(self.mutate(tool, session=f'tool-{index}', file_path=str(self.repo / 'changed.txt')))
        self.assertEqual(self.calls('create'), [])
        for index, tool in enumerate(('Edit', 'Write', 'MultiEdit', 'NotebookEdit')):
            with self.subTest(tool=tool, step='auto'):
                self.assert_allowed(self.auto_edit(tool, session=f'tool2-{index}', file_path=str(self.repo / 'changed.txt')))
        self.assertEqual(len(self.calls('create')), 4)

    def test_read_only_session_causes_no_create_and_no_state_needed(self):
        for command in ['git status', 'ls -la', 'cat f | wc -l', 'git log --oneline | head'] * 3:
            self.settle(self.bash(command, session='ro'))
        self.assertEqual(self.calls('create'), [])

    # --- contract 4: Bash classification ---

    def test_bash_not_mutating(self):
        xdg = self.env['XDG_RUNTIME_DIR']
        commands = ["grep 'a|b' f", 'rg "x;y" src', 'git status', 'git log --oneline | head', 'ls -la', 'cat f | wc -l',
                    'rm /tmp/x', 'rm -rf /tmp/dir/y', f'touch {xdg}/z', 'echo hi > /dev/null', 'ls 2>&1',
                    'cmd 2>/dev/null', 'echo x > /tmp/out.txt', 'echo "a > b"', 'python3 script.py', 'make test',
                    'git fetch', 'docker ps', 'curl https://example.test/', 'echo "rm f"', "grep 'git push' f"]
        for index, command in enumerate(commands):
            with self.subTest(command=command):
                self.settle(self.bash(command, session=f'ro-{index}'))
        self.assertEqual(self.calls('create'), [])

    def test_bash_mutating(self):
        commands = ['echo x > f', 'echo x >> f', 'rm f', 'rm /tmp/x f', 'mv a b', 'cp a b', 'tee f', 'sed -i s/a/b/ f',
                    'touch f', 'mkdir d', "git commit -m 'x'", 'git push', 'git merge x', 'git reset --hard',
                    'git checkout x', 'git add f', 'git rebase main', 'git stash', 'git cherry-pick x',
                    'docker compose up -d', 'docker compose down', 'npm install', 'composer install',
                    'curl -X POST https://example.test/', 'curl -d a=b https://example.test/',
                    'git status; touch f', 'ls && rm f', 'true | tee f']
        for index, command in enumerate(commands):
            with self.subTest(command=command):
                self.assert_denied(self.bash(command, session=f'mut-{index}'))
                self.assertEqual(self.calls('create'), [])

    # --- contract 8: recover lists orphaned breadcrumbs ---

    def dead_pid(self):
        child = subprocess.Popen([sys.executable, '-c', 'pass'])
        child.wait()
        return child.pid

    def write_state(self, session, **state):
        self.state.mkdir(exist_ok=True)
        (self.state / f'{session}.json').write_text(json.dumps(state))

    def crumb(self, pid, prompt='Half done refactor', cwd='/work/orphan', branch='feat-x'):
        return {'prompt': prompt, 'cwd': cwd, 'branch': branch, 'ts': int(time.time()), 'pid': pid}

    def test_recover_lists_dead_session_breadcrumbs_and_skips_the_rest(self):
        self.write_state('dead-sess', breadcrumb=self.crumb(self.dead_pid()), claims={})
        self.write_state('live-sess', breadcrumb=self.crumb(os.getpid(), prompt='LIVEPROMPT'), claims={})
        self.write_state('auto-sess', breadcrumb=self.crumb(self.dead_pid(), prompt='AUTOPROMPT'), claims={}, auto={'task': '9'})
        self.write_state('claim-sess', breadcrumb=self.crumb(self.dead_pid(), prompt='CLAIMPROMPT'), claims={'5': {'token': 'x'}})
        context = self.hook('recover', hook_event_name='SessionStart')['hookSpecificOutput']['additionalContext']
        for value in ('dead-sess', '/work/orphan', 'feat-x', 'Half done refactor'):
            self.assertIn(value, context)
        for value in ('live-sess', 'auto-sess', 'claim-sess', 'LIVEPROMPT', 'AUTOPROMPT', 'CLAIMPROMPT'):
            self.assertNotIn(value, context)

    def test_recover_lists_breadcrumbs_when_dibs_offline(self):
        self.write_state('dead-sess', breadcrumb=self.crumb(self.dead_pid()), claims={})
        out = self.hook('recover', env={'DIBS_CLI': '/nonexistent/dibs'}, hook_event_name='SessionStart')
        context = out['hookSpecificOutput']['additionalContext']
        self.assertIn('dead-sess', context)
        self.assertIn('Half done refactor', context)

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

    # --- contract 9 ---

    def test_settings_guard_hook_warns_on_failure(self):
        settings = json.loads((HOOK.parents[1] / 'settings.json').read_text())
        entries = [h for g in settings['hooks']['PreToolUse'] for h in g['hooks'] if h['command'].endswith('dibs-block.py guard')]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['onFailure'], 'continue')
        matchers = [g.get('matcher') for g in settings['hooks']['PreToolUse']
                    if any(h['command'].endswith('dibs-block.py guard') for h in g['hooks'])]
        self.assertEqual(matchers, ['*'])


if __name__ == '__main__':
    unittest.main()
