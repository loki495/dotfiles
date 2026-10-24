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

    def run_hook(self, stub_body, session='sess-1', env=None):
        stub = Path(self.tmp.name) / 'claims'
        stub.write_text('#!/usr/bin/env bash\n' + stub_body + '\n')
        stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
        return subprocess.run([str(HOOK)], input=json.dumps({'session_id': session, 'hook_event_name': 'Stop'}),
                              capture_output=True, text=True,
                              env={**os.environ, 'DIBS_CLAIMS_CMD': str(stub),
                                   'STOP_GATE_STATE_DIR': str(Path(self.tmp.name) / 'state'), **(env or {})})

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
