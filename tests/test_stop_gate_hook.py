"""ai/hooks/stop-gate.sh: blocks a Stop while the session holds a live Dibs claim, capped per session."""
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest

HOOK = Path(__file__).resolve().parents[1] / 'ai' / 'hooks' / 'stop-gate.sh'


class StopGateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def run_hook(self, stub_body, session='sess-1', env=None, extra=None):
        stub = Path(self.tmp.name) / 'claims'
        stub.write_text('#!/usr/bin/env bash\n' + stub_body + '\n')
        stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
        return subprocess.run([str(HOOK)], input=json.dumps({'session_id': session, 'hook_event_name': 'Stop', **(extra or {})}),
                              capture_output=True, text=True,
                              env={**os.environ, 'DIBS_CLAIMS_CMD': str(stub),
                                   'STOP_GATE_STATE_DIR': str(Path(self.tmp.name) / 'state'), **(env or {})})

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

    def test_blocks_while_a_claim_is_held_and_passes_the_session_id(self):
        proc = self.run_hook('case "$*" in *"--held-by=sess-1"*) echo \'[{"issueId":7}]\';; *) echo "[]";; esac')
        out = json.loads(proc.stdout)
        self.assertEqual(out['decision'], 'block')
        self.assertIn('task 7', out['reason'])
        self.assertIn('DIBS_STOP_GATE=off', out['reason'])

    def test_allows_with_a_warning_once_the_cap_is_reached(self):
        for _ in range(2):
            self.assertEqual(json.loads(self.run_hook(self.HELD).stdout)['decision'], 'block')
        out = json.loads(self.run_hook(self.HELD).stdout)
        self.assertNotIn('decision', out)
        self.assertIn('cap (2)', out['systemMessage'])

    def test_cap_is_per_session(self):
        for _ in range(2):
            self.run_hook(self.HELD)
        self.assertEqual(json.loads(self.run_hook(self.HELD, session='sess-2').stdout)['decision'], 'block')

    def test_cap_is_configurable(self):
        self.assertIn('systemMessage', json.loads(self.run_hook(self.HELD, env={'STOP_GATE_CAP': '0'}).stdout))

    def test_a_corrupt_counter_file_counts_as_zero(self):
        state = Path(self.tmp.name) / 'state'
        state.mkdir()
        (state / 'sess-1').write_text('$(touch pwned)')
        self.assertEqual(json.loads(self.run_hook(self.HELD).stdout)['decision'], 'block')

    def test_override_skips_the_gate(self):
        proc = self.run_hook(self.HELD, env={'DIBS_STOP_GATE': 'off'})
        self.assertEqual((proc.returncode, proc.stdout.strip()), (0, ''))

    def test_allows_with_a_warning_when_dibs_is_unreachable(self):
        proc = self.run_hook('exit 1')
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
