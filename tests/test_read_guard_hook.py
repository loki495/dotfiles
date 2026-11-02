"""ai/hooks/read-guard.sh: denies whole-file Reads of large text files, passes everything else."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

HOOK = Path(__file__).resolve().parents[1] / 'ai' / 'hooks' / 'read-guard.sh'


def run(lines, tool_input=None, name='big.php', env=None):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / name
        path.write_text('x\n' * lines)
        payload = {'tool_name': 'Read', 'tool_input': {'file_path': str(path), **(tool_input or {})}}
        return subprocess.run([str(HOOK)], input=json.dumps(payload), capture_output=True, text=True,
                              env={**os.environ, **(env or {})})


def decision(proc):
    return json.loads(proc.stdout)['hookSpecificOutput']['permissionDecision'] if proc.stdout.strip() else None


class ReadGuardHookTest(unittest.TestCase):
    def test_denies_whole_read_of_large_file(self):
        proc = run(401)
        self.assertEqual(decision(proc), 'deny')
        self.assertIn('401 lines', proc.stdout)

    def test_allows_small_file(self):
        self.assertIsNone(decision(run(400)))

    def test_allows_large_file_with_limit_or_offset(self):
        self.assertIsNone(decision(run(1000, {'limit': 50})))
        self.assertIsNone(decision(run(1000, {'offset': 10})))
        self.assertIsNone(decision(run(1000, {'allow_large': True})))

    def test_allows_images_and_pdfs(self):
        self.assertIsNone(decision(run(1000, name='scan.PDF')))
        self.assertIsNone(decision(run(1000, name='shot.png')))

    def test_threshold_and_off_switch(self):
        self.assertEqual(decision(run(60, env={'READ_GUARD_LINES': '50'})), 'deny')
        self.assertIsNone(decision(run(1000, env={'READ_GUARD': 'off'})))

    def test_missing_file_passes(self):
        payload = {'tool_name': 'Read', 'tool_input': {'file_path': '/nonexistent/zz'}}
        proc = subprocess.run([str(HOOK)], input=json.dumps(payload), capture_output=True, text=True)
        self.assertEqual((proc.returncode, proc.stdout), (0, ''))


if __name__ == '__main__':
    unittest.main()
