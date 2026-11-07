"""Reconciler claim ownership around a queued atlas refresh, with no Dibs calls."""
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / 'ai' / 'scripts' / 'atlas-refresh.py'


class AtlasClaimTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        env = {'ATLAS_QUEUE': str(Path(self.tmp.name) / 'queue'),
               'DIBS_ATLAS_HINTS': str(Path(self.tmp.name) / 'hints'),
               'ATLAS_RECONCILE_LOCK': str(Path(self.tmp.name) / 'reconcile.lock')}
        environment = mock.patch.dict(os.environ, env)
        environment.start()
        self.addCleanup(environment.stop)
        loader = importlib.machinery.SourceFileLoader('claims_ar', str(SCRIPT))
        self.ar = importlib.util.module_from_spec(importlib.util.spec_from_loader('claims_ar', loader))
        loader.exec_module(self.ar)
        self.ar.append_jsonl(self.ar.QUEUE, {'ts': 1, 'repo': '/r', 'head': 'h'})
        self.events = []
        self.fail_lookup = False
        self.fail_claim = None
        self.fail_release = None
        self.fail_heartbeat = None
        self.children = [
            {'id': 10, 'state': 'OPEN', 'parentId': 919, 'body': 'Key: reconciler:atlas:Sessioneer:abcdef0\n'},
            {'id': 11, 'state': 'OPEN', 'parentId': 919, 'body': 'Key: reconciler:atlas:Sessioneer:1234567\n'},
            {'id': 12, 'state': 'OPEN', 'parentId': 919, 'body': 'Key: reconciler:atlas:SessioneerExtra:abcdef0\n'},
            {'id': 13, 'state': 'CLOSED', 'parentId': 919, 'body': 'Key: reconciler:atlas:Sessioneer:7654321\n'},
        ]

    def dibs(self, command, *args):
        self.events.append((command, *args))
        if command in ('todo:agent:list', 'todo:agent:search'):
            if self.fail_lookup:
                raise RuntimeError('Dibs unavailable')
            return {'tasks': [{'id': 919, 'title': 'Reconciler findings', 'state': 'OPEN'}, *self.children]}
        if command == 'todo:agent:show':
            if self.fail_lookup:
                raise RuntimeError('Dibs unavailable')
            task_id = int(args[0])
            if task_id == 7:
                return {'id': 7, 'title': 'Feature atlas: Sessioneer', 'body': 'Repo: /r\nBranch: master\nVerified at: abcdef0\n'}
            if task_id == 919:
                return {'id': 919, 'title': 'Reconciler findings', 'children': self.children}
            return next(c for c in self.children if c['id'] == task_id)
        if command == 'todo:agent:claim':
            if int(args[0]) == self.fail_claim:
                raise RuntimeError('claim refused')
            return {'capability_token': 'token-' + str(args[0])}
        if command == 'todo:agent:release':
            if int(args[0]) == self.fail_release:
                raise RuntimeError('release failed')
            return {'released': True}
        if command == 'todo:agent:heartbeat':
            if int(args[0]) == self.fail_heartbeat:
                raise RuntimeError('heartbeat failed')
            return {'ok': True}
        raise AssertionError((command, args))

    def run_refresh(self, refresh_error=False, refresh_result=True, multi=False):
        inventory = {'core': ['src/'], 'ui': ['ui/']} if multi else {'core': ['src/']}
        before = (7, inventory, ['core', 'ui'] if multi else ['core'])
        after = (7, inventory, ['ui'] if multi else [])
        results = [before, after, (7, inventory, [])] if multi else [before, after]
        def refresh(repo, subsystem):
            self.events.append(('launch', repo, subsystem))
            if refresh_error:
                raise RuntimeError('launch failed')
            return refresh_result
        with mock.patch.object(self.ar, 'quota_pct', return_value=10), \
                mock.patch.object(self.ar, 'stale_subsystems', side_effect=results), \
                mock.patch.object(self.ar.DM, 'dibs_json', side_effect=self.dibs), \
                mock.patch.object(self.ar, 'refresh', side_effect=refresh), \
                mock.patch.object(self.ar, 'sync_hints'):
            self.ar.run(nightly=False)

    def ids(self, command):
        return [int(event[1]) for event in self.events if event[0] == command]

    def assert_queued(self):
        self.assertEqual([q['repo'] for q in self.ar.read_jsonl(self.ar.QUEUE)], ['/r'])

    def test_claims_all_exact_open_matches_before_launch_and_releases(self):
        self.run_refresh()
        self.assertCountEqual(self.ids('todo:agent:claim'), [10, 11])
        self.assertCountEqual(self.ids('todo:agent:release'), [10, 11])
        for event in (e for e in self.events if e[0] == 'todo:agent:claim'):
            self.assertEqual(event[event.index('--minutes') + 1], '60')
        for event in (e for e in self.events if e[0] in ('todo:agent:heartbeat', 'todo:agent:release')):
            self.assertEqual(event[event.index('--token') + 1], 'token-' + event[1])
        launch = next(i for i, e in enumerate(self.events) if e[0] == 'launch')
        self.assertTrue(all(i < launch for i, e in enumerate(self.events) if e[0] == 'todo:agent:claim'))
        self.assertEqual(self.ar.read_jsonl(self.ar.QUEUE), [])

    def test_lookup_failure_never_launches_and_retains_queue(self):
        self.fail_lookup = True
        self.run_refresh()
        self.assertNotIn('launch', [event[0] for event in self.events])
        self.assert_queued()

    def test_failed_claim_releases_previous_claim_and_never_launches(self):
        self.fail_claim = 11
        self.run_refresh()
        self.assertIn(10, self.ids('todo:agent:release'))
        self.assertNotIn('launch', [event[0] for event in self.events])
        self.assert_queued()

    def test_launch_exception_releases_all_and_retains_queue(self):
        self.run_refresh(refresh_error=True)
        self.assertCountEqual(self.ids('todo:agent:release'), [10, 11])
        self.assert_queued()

    def test_unsuccessful_launch_releases_all_and_retains_queue(self):
        self.run_refresh(refresh_result=False)
        self.assertCountEqual(self.ids('todo:agent:release'), [10, 11])
        self.assert_queued()

    def test_release_failure_retains_queue(self):
        self.fail_release = 10
        self.run_refresh()
        self.assertIn(11, self.ids('todo:agent:release'))
        self.assert_queued()

    def test_no_matching_tasks_refreshes_without_claim(self):
        self.children = [c for c in self.children if c['id'] in (12, 13)]
        self.run_refresh()
        self.assertEqual(self.ids('todo:agent:claim'), [])
        self.assertIn('launch', [event[0] for event in self.events])
        self.assertEqual(self.ar.read_jsonl(self.ar.QUEUE), [])

    def test_missing_stamp_key_is_a_matching_reconciler_finding(self):
        self.children = [{'id': 14, 'state': 'OPEN', 'parentId': 919,
                          'body': 'Key: reconciler:atlas:Sessioneer:-\n'}]
        self.run_refresh()
        self.assertEqual(self.ids('todo:agent:claim'), [14])
        self.assertEqual(self.ids('todo:agent:release'), [14])
        self.assertIn('launch', [event[0] for event in self.events])

    def test_each_launch_is_preceded_by_heartbeat_for_every_claim(self):
        self.run_refresh(multi=True)
        launches = [i for i, e in enumerate(self.events) if e[0] == 'launch']
        self.assertEqual(len(launches), 2)
        previous_launch = -1
        for launch in launches:
            interval = self.events[previous_launch + 1:launch]
            heartbeats = [int(e[1]) for e in interval if e[0] == 'todo:agent:heartbeat']
            self.assertCountEqual(heartbeats, [10, 11])
            previous_launch = launch

    def test_failed_heartbeat_prevents_launch_and_releases_claims(self):
        self.fail_heartbeat = 10
        self.run_refresh()
        self.assertNotIn('launch', [event[0] for event in self.events])
        self.assertCountEqual(self.ids('todo:agent:release'), [10, 11])
        self.assert_queued()


if __name__ == '__main__':
    unittest.main()
