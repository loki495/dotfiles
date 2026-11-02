"""ai/scripts/atlas-refresh.py: pending section, queue deferral, refresh run, hook install."""
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / 'ai' / 'scripts' / 'atlas-refresh.py'


def load(tmp):
    os.environ['DIBS_ATLAS_HINTS'] = str(tmp / 'hints.jsonl')
    os.environ['ATLAS_QUEUE'] = str(tmp / 'queue.jsonl')
    loader = importlib.machinery.SourceFileLoader('ar', str(SCRIPT))
    mod = importlib.util.module_from_spec(importlib.util.spec_from_loader('ar', loader))
    loader.exec_module(mod)
    return mod


class AtlasRefreshTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: subprocess.run(['rm', '-rf', str(self.tmp)]))
        self.ar = load(self.tmp)

    def hint(self, ts, sub, repo='/r'):
        return {'ts': ts, 'repo': repo, 'head': 'a' * 40, 'subsystem': sub, 'change': 'did x'}

    def test_section_is_added_replaced_and_removed(self):
        body = 'Repo: /r\nVerified at: abc\n'
        once = self.ar.with_section(body, [self.hint(1, 'core')])
        self.assertIn('## Pending since last refresh\n- core: did x (aaaaaaaaa, 1970-01-01)', once)
        twice = self.ar.with_section(once, [self.hint(1, 'core'), self.hint(2, 'ui')])
        self.assertEqual(twice.count('## Pending since last refresh'), 1)
        self.assertIn('- ui: did x', twice)
        self.assertEqual(self.ar.with_section(twice, []).strip(), body.strip())

    def test_section_keeps_following_headings(self):
        body = 'Intro\n\n## Pending since last refresh\n- old\n\n## Other\nkeep\n'
        out = self.ar.with_section(body, [self.hint(1, 'core')])
        self.assertIn('## Other\nkeep', out)
        self.assertNotIn('- old', out)

    def test_refresh_record_clears_only_older_hints_of_that_subsystem_and_repo(self):
        recs = [self.hint(1, 'core'), self.hint(2, 'ui'), {'ts': 3, 'repo': '/r', 'refreshed': ['core']},
                self.hint(4, 'core'), self.hint(1, 'core', '/other')]
        self.assertEqual([(h['subsystem'], h['ts']) for h in self.ar.pending(recs, '/r')], [('ui', 2), ('core', 4)])

    def test_queue_defers_above_quota_and_runs_below(self):
        with mock.patch.object(self.ar.subprocess, 'Popen') as popen, mock.patch.object(self.ar, 'quota_pct', return_value=71), \
                mock.patch.object(self.ar.subprocess, 'run', return_value=mock.Mock(stdout='h\n')):
            self.ar.queue(str(self.tmp))
            popen.assert_not_called()
            self.assertEqual(len(self.ar.read_jsonl(self.ar.QUEUE)), 1)
        with mock.patch.object(self.ar.subprocess, 'Popen') as popen, mock.patch.object(self.ar, 'quota_pct', return_value=70), \
                mock.patch.object(self.ar.subprocess, 'run', return_value=mock.Mock(stdout='h\n')):
            self.ar.queue(str(self.tmp))
            popen.assert_called_once()

    def test_unknown_quota_counts_as_full(self):
        with mock.patch.object(self.ar.subprocess, 'run', side_effect=OSError('no sessioneer')):
            self.assertEqual(self.ar.quota_pct(), 100)

    def test_run_refreshes_stale_subsystems_records_them_and_empties_queue(self):
        self.ar.append_jsonl(self.ar.QUEUE, {'ts': 1, 'repo': '/r', 'head': 'h'})
        with mock.patch.object(self.ar, 'quota_pct', return_value=10), mock.patch.object(self.ar, 'stale_subsystems', return_value=['core', 'ui']), \
                mock.patch.object(self.ar, 'refresh', side_effect=[True, False]) as refresh, mock.patch.object(self.ar, 'sync_hints'):
            self.ar.run(nightly=False)
        self.assertEqual(refresh.call_count, 2)
        self.assertEqual(self.ar.read_jsonl(self.ar.HINTS)[0]['refreshed'], ['core'])
        self.assertFalse(os.path.exists(self.ar.QUEUE))

    def test_run_keeps_repo_queued_when_quota_is_high_unless_nightly(self):
        self.ar.append_jsonl(self.ar.QUEUE, {'ts': 1, 'repo': '/r', 'head': 'h'})
        with mock.patch.object(self.ar, 'quota_pct', return_value=80), mock.patch.object(self.ar, 'refresh') as refresh, mock.patch.object(self.ar, 'sync_hints'):
            self.ar.run(nightly=False)
            refresh.assert_not_called()
        self.assertEqual([q['repo'] for q in self.ar.read_jsonl(self.ar.QUEUE)], ['/r'])
        with mock.patch.object(self.ar, 'quota_pct', return_value=80), mock.patch.object(self.ar, 'stale_subsystems', return_value=['core']), \
                mock.patch.object(self.ar, 'refresh', return_value=True) as refresh, mock.patch.object(self.ar, 'sync_hints'):
            self.ar.run(nightly=True)
            refresh.assert_called_once()

    def test_install_hooks_writes_marker_hook_and_respects_foreign_hooks(self):
        for name in ('a', 'b'):
            subprocess.run(['git', 'init', '-q', str(self.tmp / name)], check=True)
        foreign = self.tmp / 'b' / '.git' / 'hooks' / 'post-merge'
        foreign.write_text('#!/bin/sh\necho mine\n')
        parents = [(str(self.tmp / n), {}) for n in ('a', 'b')]
        with mock.patch.object(self.ar, 'atlas_parents', return_value=parents):
            self.ar.install_hooks()
            self.ar.install_hooks()
        mine = self.tmp / 'a' / '.git' / 'hooks' / 'post-merge'
        self.assertIn('atlas-refresh.py', mine.read_text())
        self.assertTrue(os.access(mine, os.X_OK))
        self.assertEqual(foreign.read_text(), '#!/bin/sh\necho mine\n')


if __name__ == '__main__':
    unittest.main()
