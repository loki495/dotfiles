"""ai/hooks/claim-overlap.sh: warns (never blocks) about another live Dibs claim on the edited file."""
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest

HOOK = Path(__file__).resolve().parents[1] / 'ai' / 'hooks' / 'claim-overlap.sh'


def run(stub_body, tool_input=None, session='sess-1'):
    with tempfile.TemporaryDirectory() as tmp:
        stub = Path(tmp) / 'claims'
        stub.write_text('#!/usr/bin/env bash\n' + stub_body + '\n')
        stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
        payload = {'session_id': session, 'tool_name': 'Edit',
                   'tool_input': tool_input if tool_input is not None else {'file_path': '/srv/x/a.php'}}
        proc = subprocess.run([str(HOOK)], input=json.dumps(payload), capture_output=True, text=True,
                              env={**os.environ, 'DIBS_CLAIMS_CMD': str(stub)})
    return proc


def context(proc):
    return json.loads(proc.stdout)['hookSpecificOutput']['additionalContext'] if proc.stdout.strip() else None


class ClaimOverlapHookTest(unittest.TestCase):
    def test_warns_about_an_overlapping_claim(self):
        proc = run('echo \'[{"issueId":7,"agentName":"claude:a:1","paths":["/srv/x"]}]\'')
        self.assertEqual(proc.returncode, 0)
        self.assertIn('task 7 held by claude:a:1 on /srv/x', context(proc))

    def test_passes_path_and_session_arguments(self):
        proc = run('case "$*" in *"--path=/srv/x/a.php"*"--except-session=sess-1"*) echo \'[{"issueId":1,"agentName":"a","paths":["/srv"]}]\';; *) echo "[]";; esac')
        self.assertIn('task 1 held by a', context(proc))

    def test_silent_when_no_claim_overlaps(self):
        proc = run('echo "[]"')
        self.assertEqual((proc.returncode, proc.stdout.strip()), (0, ''))

    def test_silent_when_the_tool_has_no_file_path(self):
        proc = run('echo "[{}]"', tool_input={'command': 'ls'})
        self.assertEqual((proc.returncode, proc.stdout.strip()), (0, ''))

    def test_warns_but_does_not_block_when_dibs_is_unreachable(self):
        proc = run('exit 1')
        self.assertEqual(proc.returncode, 0)
        self.assertIn('check skipped', context(proc))

    def test_warns_but_does_not_block_on_an_unreadable_answer(self):
        proc = run('echo "not json"')
        self.assertEqual(proc.returncode, 0)
        self.assertIn('check skipped', context(proc))


if __name__ == '__main__':
    unittest.main()
