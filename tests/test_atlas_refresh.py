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

    def merged_repo(self, author):
        repo = self.tmp / 'repo'
        env = {**os.environ, 'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null'}
        def git(*a, **kw):
            subprocess.run(['git', '-C', str(repo), *a], check=True, capture_output=True, env={**env, **kw})
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True, env=env)
        git('config', 'user.email', 'me@x.test'); git('config', 'user.name', 'Me')
        (repo / 'a').write_text('1'); git('add', 'a'); git('commit', '-qm', 'one')
        git('tag', 'before')
        (repo / 'a').write_text('2')
        git('-c', f'user.email={author}', 'commit', '-qam', 'two')
        git('update-ref', 'ORIG_HEAD', 'before')
        return str(repo)

    def test_only_own_commits_may_start_a_refresh(self):
        self.assertTrue(self.ar.own_commits_only(self.merged_repo('me@x.test')))

    def test_queue_ignores_a_merge_with_foreign_commits(self):
        repo = self.merged_repo('other@x.test')
        self.assertFalse(self.ar.own_commits_only(repo))
        with mock.patch.object(self.ar, 'quota_pct', return_value=0) as quota:
            self.ar.queue(repo)
            quota.assert_not_called()
        self.assertFalse(os.path.exists(self.ar.QUEUE))

    def test_queue_defers_above_quota_and_runs_below(self):
        with mock.patch.object(self.ar, 'own_commits_only', return_value=True), mock.patch.object(self.ar.subprocess, 'Popen') as popen, mock.patch.object(self.ar, 'quota_pct', return_value=71), \
                mock.patch.object(self.ar.subprocess, 'run', return_value=mock.Mock(stdout='h\n')):
            self.ar.queue(str(self.tmp))
            popen.assert_not_called()
            self.assertEqual(len(self.ar.read_jsonl(self.ar.QUEUE)), 1)
        with mock.patch.object(self.ar, 'own_commits_only', return_value=True), mock.patch.object(self.ar.subprocess, 'Popen') as popen, mock.patch.object(self.ar, 'quota_pct', return_value=70), \
                mock.patch.object(self.ar.subprocess, 'run', return_value=mock.Mock(stdout='h\n')):
            self.ar.queue(str(self.tmp))
            popen.assert_called_once()

    def test_unknown_quota_counts_as_full(self):
        with mock.patch.object(self.ar.subprocess, 'run', side_effect=OSError('no sessioneer')):
            self.assertEqual(self.ar.quota_pct(), 100)

    def test_partial_refresh_records_success_and_keeps_repository_for_retry(self):
        self.ar.append_jsonl(self.ar.QUEUE, {'ts': 1, 'repo': '/r', 'head': 'h'})
        self.ar.append_jsonl(self.ar.HINTS, self.hint(1, 'core'))
        self.ar.append_jsonl(self.ar.HINTS, self.hint(1, 'ui'))
        responses = [mock.Mock(returncode=0, stdout=json.dumps(value), stderr='') for value in (
            {'atlas': 7, 'subsystems': [{'id': 'core', 'owned': ['src/']}, {'id': 'ui', 'owned': ['ui/']}], 'stale': [{'id': 'core'}, {'id': 'ui'}]},
            {'atlas': 7, 'subsystems': [{'id': 'core', 'owned': ['src/']}, {'id': 'ui', 'owned': ['ui/']}], 'stale': [{'id': 'ui'}]},
        )]
        with mock.patch.object(self.ar, 'quota_pct', return_value=10), mock.patch.object(self.ar.subprocess, 'run', side_effect=responses), \
                mock.patch.object(self.ar, 'refresh', side_effect=[True, False]) as refresh, mock.patch.object(self.ar, 'sync_hints'):
            self.ar.run(nightly=False)
        self.assertEqual(refresh.call_count, 2)
        self.assertEqual(self.ar.read_jsonl(self.ar.HINTS)[-1]['refreshed'], ['core'])
        self.assertEqual([h['subsystem'] for h in self.ar.pending(self.ar.read_jsonl(self.ar.HINTS), '/r')], ['ui'])
        self.assertEqual([q['repo'] for q in self.ar.read_jsonl(self.ar.QUEUE)], ['/r'])

    def run_with_helper_results(self, results):
        self.ar.append_jsonl(self.ar.QUEUE, {'ts': 1, 'repo': '/r', 'head': 'h'})
        responses = [mock.Mock(returncode=code, stdout=stdout, stderr='helper error')
                     for code, stdout in results]
        with mock.patch.object(self.ar, 'quota_pct', return_value=10), \
                mock.patch.object(self.ar.subprocess, 'run', side_effect=responses) as helper, \
                mock.patch.object(self.ar, 'refresh', return_value=True) as refresh, \
                mock.patch.object(self.ar, 'sync_hints'):
            try:
                self.ar.run(nightly=False)
            except (RuntimeError, ValueError):
                pass
        self.assertEqual(helper.call_count, len(results))
        return refresh

    def test_unverifiable_initial_helper_result_retains_queue(self):
        for result in [(1, ''), (0, '{"skipped": "Dibs unavailable"}'),
                       (0, '{}'), (0, 'not json'), (0, '{"atlas": 7}'),
                       (0, '{"atlas": 7, "subsystems": [], "stale": []}')]:
            with self.subTest(result=result):
                for path in (self.ar.QUEUE, self.ar.HINTS):
                    if os.path.exists(path):
                        os.remove(path)
                refresh = self.run_with_helper_results([result])
                refresh.assert_not_called()
                self.assertEqual([q['repo'] for q in self.ar.read_jsonl(self.ar.QUEUE)], ['/r'])
                self.assertEqual(self.ar.read_jsonl(self.ar.HINTS), [])

    def test_successful_session_requires_fresh_verification_of_same_atlas(self):
        initial = (0, '{"atlas": 7, "subsystems": [{"id": "core", "owned": ["src/", "docs/"]}], "stale": [{"id": "core"}]}')
        for after in [(0, '{"atlas": 7, "subsystems": [{"id": "core", "owned": ["src/", "docs/"]}], "stale": [{"id": "core"}]}'),
                      (0, '{"atlas": 8, "subsystems": [{"id": "core", "owned": ["src/", "docs/"]}], "stale": []}'),
                      (0, '{"atlas": 7, "subsystems": [], "stale": []}'),
                      (0, '{"atlas": 7, "subsystems": [{"id": "core", "owned": []}], "stale": []}'),
                      (0, '{"atlas": 7, "subsystems": [{"id": "core", "owned": ["src/"]}], "stale": []}'),
                      (0, '{"atlas": 7, "subsystems": [{"id": "core", "owned": ["src/app/", "docs/"]}], "stale": []}'),
                      (0, '{"atlas": 7, "stale": []}'),
                      (0, '{"skipped": "Dibs unavailable"}'),
                      (1, '')]:
            with self.subTest(after=after):
                for path in (self.ar.QUEUE, self.ar.HINTS):
                    if os.path.exists(path):
                        os.remove(path)
                self.run_with_helper_results([initial, after]).assert_called_once_with('/r', 'core')
                self.assertEqual([q['repo'] for q in self.ar.read_jsonl(self.ar.QUEUE)], ['/r'])
                self.assertEqual(self.ar.read_jsonl(self.ar.HINTS), [])

    def test_confirmed_refresh_clears_queue_and_records_subsystem(self):
        self.run_with_helper_results([
            (0, '{"atlas": 7, "subsystems": [{"id": "core", "owned": ["src/", "docs/"]}], "stale": [{"id": "core"}]}'),
            (0, '{"atlas": 7, "subsystems": [{"id": "core", "owned": ["src/", "docs/", "tests/"]}], "stale": []}'),
        ]).assert_called_once_with('/r', 'core')
        self.assertEqual(self.ar.read_jsonl(self.ar.QUEUE), [])
        self.assertEqual(self.ar.read_jsonl(self.ar.HINTS)[0]['refreshed'], ['core'])

    def test_queue_entries_added_during_refresh_survive_even_for_same_repo(self):
        self.ar.append_jsonl(self.ar.QUEUE, {'ts': 1, 'repo': '/r', 'head': 'old'})
        def refresh(repo, subsystem):
            self.ar.append_jsonl(self.ar.QUEUE, {'ts': 2, 'repo': '/r', 'head': 'new'})
            self.ar.append_jsonl(self.ar.QUEUE, {'ts': 2, 'repo': '/other', 'head': 'other'})
            return True
        before = (7, {'core': ['src/']}, ['core'])
        after = (7, {'core': ['src/']}, [])
        with mock.patch.object(self.ar, 'quota_pct', return_value=10), \
                mock.patch.object(self.ar, 'stale_subsystems', side_effect=[before, after]), \
                mock.patch.object(self.ar, 'refresh', side_effect=refresh), \
                mock.patch.object(self.ar, 'sync_hints'):
            self.ar.run(nightly=False)
        queued = self.ar.read_jsonl(self.ar.QUEUE)
        self.assertIn({'ts': 2, 'repo': '/r', 'head': 'new'}, queued)
        self.assertIn({'ts': 2, 'repo': '/other', 'head': 'other'}, queued)

    def test_hint_added_during_refresh_remains_pending(self):
        self.ar.append_jsonl(self.ar.QUEUE, {'ts': 1, 'repo': '/r', 'head': 'old'})
        self.ar.append_jsonl(self.ar.HINTS, self.hint(10, 'core'))
        def refresh(repo, subsystem):
            self.ar.append_jsonl(self.ar.HINTS, self.hint(20, 'core'))
            return True
        before = (7, {'core': ['src/']}, ['core'])
        after = (7, {'core': ['src/']}, [])
        with mock.patch.object(self.ar, 'quota_pct', return_value=10), \
                mock.patch.object(self.ar, 'stale_subsystems', side_effect=[before, after]), \
                mock.patch.object(self.ar, 'refresh', side_effect=refresh), \
                mock.patch.object(self.ar.time, 'time', return_value=20), \
                mock.patch.object(self.ar, 'sync_hints'):
            self.ar.run(nightly=False)
        pending = self.ar.pending(self.ar.read_jsonl(self.ar.HINTS), '/r')
        self.assertEqual([h['ts'] for h in pending], [20])

    def test_run_keeps_repo_queued_when_quota_is_high_unless_nightly(self):
        self.ar.append_jsonl(self.ar.QUEUE, {'ts': 1, 'repo': '/r', 'head': 'h'})
        with mock.patch.object(self.ar, 'quota_pct', return_value=80), mock.patch.object(self.ar, 'refresh') as refresh, mock.patch.object(self.ar, 'sync_hints'):
            self.ar.run(nightly=False)
            refresh.assert_not_called()
        self.assertEqual([q['repo'] for q in self.ar.read_jsonl(self.ar.QUEUE)], ['/r'])
        with mock.patch.object(self.ar, 'quota_pct', return_value=80), mock.patch.object(self.ar, 'stale_subsystems', side_effect=[(7, {'core': ['src/']}, ['core']), (7, {'core': ['src/']}, [])]) as stale, \
                mock.patch.object(self.ar, 'refresh', return_value=True) as refresh, mock.patch.object(self.ar, 'sync_hints'):
            self.ar.run(nightly=True)
            refresh.assert_called_once_with('/r', 'core')
            self.assertEqual(stale.call_count, 2)
        self.assertEqual(self.ar.read_jsonl(self.ar.QUEUE), [])
        self.assertEqual(self.ar.read_jsonl(self.ar.HINTS)[0]['refreshed'], ['core'])

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
