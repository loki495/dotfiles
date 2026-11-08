"""ai/hooks/stop-gate.sh: status line first, then the dibs block / [complete] lines, then a status-dependent claim check."""
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dibs_block_hook import STUB as DIBS_STUB  # noqa: E402

HOOK = Path(__file__).resolve().parents[1] / 'ai' / 'hooks' / 'stop-gate.sh'
BLOCK = Path(__file__).resolve().parents[1] / 'ai' / 'hooks' / 'dibs-block.py'
SAFE = 'Safe to archive this session.'
DONE = 'All planned work is done.'
SAME = 'Continue in this session: finishing the tests.'
OTHER = 'Continue in a different session: the infra half.'
ANDRES = 'Waiting on Andres: a decision.'
WORK = 'Waiting on other work: job 8.'


class StopGateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        t = Path(self.tmp.name)
        (t / 'dibs-stub.py').write_text(DIBS_STUB)
        self.db = t / 'db.json'
        self.db.write_text(json.dumps({'log': [], 'claims': {}, 'issues': {
            '5': {'state': 'OPEN', 'body': 'Goal.', 'revision': 1}, '6': {'state': 'CLOSED', 'body': '', 'revision': 1}}}))
        self.repo = t / 'repo'
        self.repo.mkdir()
        git = ['git', '-C', str(self.repo), '-c', 'user.name=t', '-c', 'user.email=t@t']
        subprocess.run(git + ['init', '-q'], check=True)
        subprocess.run(git + ['commit', '-q', '--allow-empty', '-m', 'one'], check=True)
        self.sha = subprocess.run(git + ['rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
        # never the real Dibs: the dibs-block stop step run by the gate talks to this stub
        self.safe_env = {'DIBS_CLI': f'{sys.executable} {t / "dibs-stub.py"} {self.db}', 'DIBS_BLOCK_STATE_DIR': str(t / 'bstate'),
                         'DIBS_ATLAS_HINTS': str(t / 'hints.jsonl'), 'DIBS_ATLAS_SYNC': 'off', 'DIBS_AGENT_PID': '4242',
                         'SESSIONEER_SELF': 'tester'}

    def dbs(self):
        return json.loads(self.db.read_text())

    def calls(self, cmd):
        return [c for c in self.dbs()['log'] if c[0] == cmd]

    def run_hook(self, stub_body, session='sess-1', env=None, extra=None):
        stub = Path(self.tmp.name) / 'claims'
        stub.write_text('#!/usr/bin/env bash\n' + stub_body + '\n')
        stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
        return subprocess.run([str(HOOK)], input=json.dumps({'session_id': session, 'hook_event_name': 'Stop',
                                                              'cwd': str(self.repo), **(extra or {})}),
                              capture_output=True, text=True,
                              env={**os.environ, **self.safe_env, 'DIBS_CLAIMS_CMD': str(stub),
                                   'STOP_GATE_STATE_DIR': str(Path(self.tmp.name) / 'state'), **(env or {})})

    def claim_five_via_block(self):
        p = subprocess.run([sys.executable, str(BLOCK), 'stop'], text=True, capture_output=True, env={**os.environ, **self.safe_env},
                           input=json.dumps({'session_id': 'sess-1', 'cwd': str(self.repo),
                                             'last_assistant_message': '```dibs\nclaim 5\n```'}))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('5', self.dbs()['claims'])

    def dibs_claims_stub(self):
        """A claims answer read from the same fake Dibs the block step writes to."""
        return f'{sys.executable} {Path(self.tmp.name) / "dibs-stub.py"} {self.db} todo:agent:claims "$@"'

    def test_blocks_a_final_message_without_the_status_line_once_per_turn(self):
        out = json.loads(self.run_hook('echo "[]"', extra={'last_assistant_message': 'Done.'}).stdout)
        self.assertEqual(out['decision'], 'block')
        self.assertIn('Rule 1226', out['reason'])
        self.assertIn('output only the missing status line', out['reason'])
        self.assertIn('ask it with AskUserQuestion first', out['reason'])
        self.assertIn('handed this session', out['reason'])
        again = self.run_hook('echo "[]"', extra={'last_assistant_message': 'Done.', 'stop_hook_active': True})
        self.assertEqual(again.stdout.strip(), '')

    def test_allows_each_status_line(self):
        for line in ('Safe to archive this session.', 'Continue in this session: x.',
                     'Continue in a different session: y.', 'Waiting on Andres: a decision.', 'Waiting on other work: job 8.', 'All planned work is done.'):
            proc = self.run_hook('echo "[]"', extra={'last_assistant_message': 'Report.\n' + line})
            self.assertEqual(proc.stdout.strip(), '', line)

    def status_run(self, msg, **extra):
        return self.run_hook('echo "[]"', extra={'last_assistant_message': msg, **extra})

    def test_phrase_in_last_three_nonempty_lines_passes_ignoring_trailing_blanks(self):
        ph = 'Waiting on Andres: a decision.'
        for msg in (ph, f'a\nb\n{ph}\n\n\n', f'a\n{ph}\nx\n\ny\n', f'a\n{ph}\nx\ny'):
            self.assertEqual(self.status_run(msg).stdout.strip(), '', repr(msg))

    def test_phrase_earlier_than_the_last_three_nonempty_lines_blocks_with_1226(self):
        ph = 'All planned work is done.'
        for msg in (f'{ph}\nb\nc\nd', f'{ph}\n\nb\n\nc\nd\n\n', f'I said "{ph}" earlier.\nb\nc\nd'):
            out = json.loads(self.status_run(msg).stdout)
            self.assertEqual(out['decision'], 'block', repr(msg))
            self.assertIn('1226', out['reason'])

    def test_misplaced_phrase_is_not_blocked_when_stop_hook_active(self):
        proc = self.status_run('All planned work is done.\nb\nc\nd', stop_hook_active=True)
        self.assertEqual(proc.stdout.strip(), '')

    def test_absent_message_is_not_blocked(self):
        self.assertEqual(self.run_hook('echo "[]"').stdout.strip(), '')

    HELD = 'echo \'[{"issueId":7,"agentName":"claude:a:sess-1","paths":[]}]\''

    def test_allows_when_no_claim_is_held(self):
        proc = self.run_hook('echo "[]"')
        self.assertEqual((proc.returncode, proc.stdout.strip()), (0, ''))

    # --- strict order: status line, then dibs block / [complete], then the claim check ---

    def test_missing_status_asks_only_for_it_and_runs_nothing_else(self):
        msg = f'Done.\n\n```dibs\nclaim 5\n```\n{'[complete 5 | sha=abc1234 | notes]'}'
        out = json.loads(self.run_hook(self.HELD, extra={'last_assistant_message': msg}).stdout)
        self.assertEqual(out['decision'], 'block')
        self.assertIn('Rule 1226', out['reason'])
        self.assertIn('[complete', out['reason'])
        self.assertIn('dibs', out['reason'])
        self.assertEqual(self.dbs()['log'], [])
        self.assertEqual(self.dbs()['claims'], {})

    def test_missing_status_blocks_before_the_claim_check_even_with_a_claim_held(self):
        out = json.loads(self.run_hook(self.HELD, extra={'last_assistant_message': 'Done.'}).stdout)
        self.assertIn('Rule 1226', out['reason'])
        self.assertNotIn('task 7', out['reason'])

    def test_with_status_present_the_dibs_block_is_applied_first(self):
        msg = f'Done.\n```dibs\nclaim 5\nnote 5: x\n```\n{SAFE}'
        self.run_hook('echo "[]"', extra={'last_assistant_message': msg})
        self.assertEqual(len(self.calls('claim')), 1)
        self.assertEqual(len(self.calls('comment')), 1)

    def test_complete_line_in_the_message_is_applied_by_the_gate(self):
        self.claim_five_via_block()
        msg = f'Report.\n[complete 5 | sha={self.sha[:9]} tests="none: no code" docs="none: no docs" | Fixed it]\n{DONE}'
        proc = self.run_hook(self.dibs_claims_stub(), extra={'last_assistant_message': msg})
        out = json.loads(proc.stdout)
        self.assertNotIn('decision', out)
        self.assertIn('done 5: completed', out['systemMessage'])
        self.assertEqual(self.dbs()['issues']['5']['state'], 'CLOSED')

    def test_complete_line_refusal_blocks_once_and_not_when_stop_hook_active(self):
        self.claim_five_via_block()
        msg = f'Report.\n[complete 5 | sha=deadbeef1 | Fixed it]\n{DONE}'
        out = json.loads(self.run_hook(self.dibs_claims_stub(), extra={'last_assistant_message': msg}).stdout)
        self.assertEqual(out['decision'], 'block')
        self.assertIn('does not exist', out['reason'])
        again = self.run_hook(self.dibs_claims_stub(), extra={'last_assistant_message': msg, 'stop_hook_active': True})
        self.assertNotIn('decision', json.loads(again.stdout) if again.stdout.strip() else {})

    def test_dibs_block_refusal_blocks_once(self):
        msg = f'Report.\n```dibs\nnote 5: not mine\n```\n{SAFE}'
        out = json.loads(self.run_hook('echo "[]"', extra={'last_assistant_message': msg}).stdout)
        self.assertEqual(out['decision'], 'block')
        self.assertIn('not claimed by this session', out['reason'])

    def test_status_cases_with_no_claim_all_allow(self):
        for line in (SAFE, DONE, SAME, OTHER, ANDRES, WORK):
            with self.subTest(line=line):
                self.assertEqual(self.status_run(f'Report.\n{line}').stdout.strip(), '')

    def held_run(self, line, **extra):
        return self.run_hook('case "$*" in *"--held-by=sess-1"*) echo \'[{"issueId":7}]\';; *) echo "[]";; esac',
                             extra={'last_assistant_message': f'Report.\n{line}', **extra})

    def test_continue_in_this_session_and_waiting_keep_the_claim_without_blocking(self):
        for line in (SAME, ANDRES, WORK):
            with self.subTest(line=line):
                proc = self.held_run(line)
                self.assertEqual(proc.returncode, 0)
                self.assertNotIn('decision', json.loads(proc.stdout) if proc.stdout.strip() else {})

    def test_those_statuses_renew_the_lease_of_claims_made_through_the_block(self):
        self.claim_five_via_block()
        before = len(self.calls('heartbeat'))
        for line in (SAME, ANDRES, WORK):
            proc = self.run_hook(self.dibs_claims_stub(), extra={'last_assistant_message': f'Report.\n{line}'})
            self.assertNotIn('decision', json.loads(proc.stdout) if proc.stdout.strip() else {})
        self.assertEqual(len(self.calls('heartbeat')) - before, 3)
        self.assertIn('5', self.dbs()['claims'])

    def test_successful_note_with_continue_renews_the_held_claim(self):
        self.claim_five_via_block()
        before = len(self.calls('heartbeat'))
        msg = f'```dibs\nnote 5: still working\n```\n{SAME}'
        proc = self.run_hook(self.dibs_claims_stub(), extra={'last_assistant_message': msg})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn('decision', json.loads(proc.stdout) if proc.stdout.strip() else {})
        self.assertEqual(len(self.calls('comment')), 1)
        self.assertIn('5', self.dbs()['claims'])
        self.assertEqual(len(self.calls('heartbeat')) - before, 1)

    def test_safe_or_all_done_with_a_claim_open_blocks_asking_for_complete_or_release(self):
        for line in (SAFE, DONE):
            with self.subTest(line=line):
                out = json.loads(self.held_run(line).stdout)
                self.assertEqual(out['decision'], 'block')
                self.assertIn('task 7', out['reason'])
                self.assertIn('[complete', out['reason'])
                self.assertIn('todo_release', out['reason'])

    def test_different_session_with_a_claim_open_blocks_asking_for_a_handoff_and_release(self):
        out = json.loads(self.held_run(OTHER).stdout)
        self.assertEqual(out['decision'], 'block')
        self.assertIn('task 7', out['reason'])
        self.assertIn('handoff', out['reason'])
        self.assertIn('session-handoff', out['reason'])
        self.assertIn('todo_release', out['reason'])

    def test_claim_check_passes_the_session_id(self):
        args = Path(self.tmp.name) / 'args'
        proc = self.run_hook(f'echo "$@" > {args}; echo "[]"', extra={'last_assistant_message': f'R.\n{SAFE}'})
        self.assertEqual(proc.returncode, 0)
        self.assertIn('--held-by=sess-1', args.read_text())

    def test_stop_hook_active_with_the_claim_still_open_allows_with_a_warning(self):
        for line in (SAFE, DONE, OTHER):
            with self.subTest(line=line):
                out = json.loads(self.held_run(line, stop_hook_active=True).stdout)
                self.assertNotIn('decision', out)
                self.assertTrue(out['systemMessage'])

    def test_it_blocks_every_turn_there_is_no_cap(self):
        for _ in range(4):
            self.assertEqual(json.loads(self.held_run(SAFE).stdout)['decision'], 'block')

    def test_the_old_cap_setting_has_no_effect(self):
        capped = self.run_hook(self.HELD, env={'STOP_GATE_CAP': '0'}, extra={'last_assistant_message': f'R.\n{SAFE}'})
        self.assertEqual(json.loads(capped.stdout)['decision'], 'block')
        self.assertNotIn('cap (', capped.stdout)

    def test_the_last_status_phrase_in_the_last_three_lines_decides(self):
        out = self.held_run(f'{SAFE}\n{SAME}')
        self.assertNotIn('decision', json.loads(out.stdout) if out.stdout.strip() else {})
        out = json.loads(self.held_run(f'{SAME}\n{DONE}').stdout)
        self.assertEqual(out['decision'], 'block')
        out = json.loads(self.held_run(f'{ANDRES}\n{OTHER}').stdout)
        self.assertEqual(out['decision'], 'block')
        self.assertIn('handoff', out['reason'])

    def test_a_stale_counter_file_from_the_old_gate_is_ignored(self):
        state = Path(self.tmp.name) / 'state'
        state.mkdir()
        (state / 'sess-1').write_text('9')
        self.assertEqual(json.loads(self.held_run(SAFE).stdout)['decision'], 'block')

    def test_override_skips_the_gate(self):
        proc = self.run_hook(self.HELD, env={'DIBS_STOP_GATE': 'off'})
        self.assertEqual((proc.returncode, proc.stdout.strip()), (0, ''))

    def test_override_skips_the_status_and_claim_checks_but_still_applies_the_block(self):
        msg = 'Done.\n```dibs\nclaim 5\n```'
        proc = self.run_hook(self.HELD, env={'DIBS_STOP_GATE': 'off'}, extra={'last_assistant_message': msg})
        self.assertNotIn('decision', json.loads(proc.stdout) if proc.stdout.strip() else {})
        self.assertEqual(len(self.calls('claim')), 1)

    def test_allows_with_a_warning_when_dibs_is_unreachable(self):
        proc = self.run_hook('exit 1')
        self.assertEqual(proc.returncode, 0)
        out = json.loads(proc.stdout)
        self.assertNotIn('decision', out)
        self.assertIn('skipped', out['systemMessage'])

    def test_unreachable_dibs_with_a_closing_status_allows_with_a_warning(self):
        proc = self.run_hook('exit 1', extra={'last_assistant_message': f'R.\n{SAFE}'})
        self.assertEqual(proc.returncode, 0)
        out = json.loads(proc.stdout)
        self.assertNotIn('decision', out)
        self.assertIn('skipped', out['systemMessage'])

    def test_allows_with_a_warning_on_an_unreadable_answer(self):
        out = json.loads(self.run_hook('echo "not json"').stdout)
        self.assertNotIn('decision', out)
        self.assertIn('skipped', out['systemMessage'])


if __name__ == '__main__':
    unittest.main()
