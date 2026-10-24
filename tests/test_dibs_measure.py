"""ai/scripts/dibs-measure.py: atlas drift, push-vs-atlas scan, dead claims."""
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'ai' / 'scripts' / 'dibs-measure.py'
loader = importlib.machinery.SourceFileLoader('dibs_measure', str(SCRIPT))
spec = importlib.util.spec_from_loader('dibs_measure', loader)
dm = importlib.util.module_from_spec(spec)
loader.exec_module(dm)


def tool_use(name, **inp):
    return json.dumps({'timestamp': '2026-10-20T10:00:00Z',
                       'message': {'content': [{'type': 'tool_use', 'name': name, 'input': inp}]}})


def git(repo, *args):
    subprocess.run(['git', '-C', repo, '-c', 'user.name=t', '-c', 'user.email=t@t',
                    *args], check=True, capture_output=True)


class ParseAtlasTests(unittest.TestCase):
    def test_fields(self):
        body = 'Repo: ~/x (https://h/x)\nBranch: stable (production)\nVerified at: abc1234 (note)\n'
        self.assertEqual(dm.parse_atlas(body), (os.path.expanduser('~/x'), 'stable', 'abc1234'))

    def test_missing_fields(self):
        self.assertEqual(dm.parse_atlas('no fields here'), (None, None, None))
        self.assertEqual(dm.parse_atlas(None), (None, None, None))


class AtlasDriftTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = self.tmp.name
        git(self.repo, 'init', '-q', '-b', 'main')
        for n in ('a', 'b'):
            Path(self.repo, n).write_text(n)
            git(self.repo, 'add', n)
            git(self.repo, 'commit', '-q', '-m', n)

    def tearDown(self):
        self.tmp.cleanup()

    def sha(self, ref):
        return subprocess.check_output(['git', '-C', self.repo, 'rev-parse', ref], text=True).strip()

    def test_behind_tip(self):
        body = f'Repo: {self.repo}\nBranch: main\nVerified at: {self.sha("HEAD~1")}\n'
        row = dm.atlas_drift('Feature atlas: T', body)
        self.assertEqual((row['behind'], row['files']), ('1', 1))

    def test_stamp_not_on_branch(self):
        git(self.repo, 'checkout', '-q', '-b', 'side', 'HEAD~1')
        Path(self.repo, 'c').write_text('c')
        git(self.repo, 'add', 'c')
        git(self.repo, 'commit', '-q', '-m', 'c')
        stray = self.sha('HEAD')
        git(self.repo, 'checkout', '-q', 'main')
        row = dm.atlas_drift('Feature atlas: T', f'Repo: {self.repo}\nBranch: main\nVerified at: {stray}\n')
        self.assertIn('stamp NOT on branch', row['status'])

    def test_unknown_stamp_and_missing_repo(self):
        row = dm.atlas_drift('Feature atlas: T', f'Repo: {self.repo}\nBranch: main\nVerified at: deadbee\n')
        self.assertEqual(row['status'], 'stamp unknown to repo')
        row = dm.atlas_drift('Feature atlas: T', 'Repo: /nonexistent/x\nVerified at: deadbee\n')
        self.assertEqual(row['status'], 'no repo/stamp')


class PushAtlasScanTests(unittest.TestCase):
    def scan(self, lines):
        with tempfile.TemporaryDirectory() as root:
            proj = Path(root, dm.PROJECT_PREFIX + 'demo')
            proj.mkdir()
            proj.joinpath('s.jsonl').write_text('\n'.join(lines) + '\n')
            return dm.scan_push_atlas(root, 30, time.time())

    def test_atlas_after_push(self):
        res = self.scan([tool_use('Bash', command='git push origin main'),
                         tool_use('mcp__dibs__todo_comment', body='Verified at: abc')])
        self.assertEqual(res['demo'], [1, 1, 1])

    def test_atlas_before_push_does_not_count_as_after(self):
        res = self.scan([tool_use('mcp__dibs__todo_revise', body='Verified at: abc'),
                         tool_use('Bash', command='git push')])
        self.assertEqual(res['demo'], [1, 0, 1])

    def test_malformed_and_truncated_lines_are_skipped(self):
        res = self.scan(['{"tool_use": broken', tool_use('Bash', command='git push'),
                         '{"message": {"content": [{"type": "tool_use", "na'])
        self.assertEqual(res['demo'], [1, 0, 0])

    def test_no_push_no_row(self):
        self.assertEqual(dict(self.scan([tool_use('Bash', command='ls')])), {})


class DeadClaimTests(unittest.TestCase):
    def test_only_open_dead_claims(self):
        tasks = [{'state': 'OPEN', 'claim': {'isCurrentlyAlive': False}},
                 {'state': 'OPEN', 'claim': {'isCurrentlyAlive': True}},
                 {'state': 'OPEN', 'claim': None}, {'state': 'CLOSED', 'claim': {'isCurrentlyAlive': False}}]
        self.assertEqual(len(dm.dead_claims(tasks)), 1)


class CliTests(unittest.TestCase):
    def test_unreadable_dibs_does_not_crash_or_fail(self):
        with tempfile.TemporaryDirectory() as t:
            bad = Path(t, 'atlas.json')
            bad.write_text('not json')
            p = subprocess.run(['python3', str(SCRIPT), '--atlas-json', str(bad), '--claims-json', str(bad),
                                '--projects-dir', t], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0)
        self.assertIn('Dibs unreadable', p.stderr)
        self.assertNotIn('Traceback', p.stderr)


if __name__ == '__main__':
    unittest.main()
