"""Profile-aligned, fail-closed refresh quota selection."""
import datetime
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / 'ai' / 'scripts' / 'atlas-refresh.py'
NOW = 1_800_000_000


class AtlasQuotaTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def load(self, profile=None, threshold=None):
        env = {'ATLAS_QUEUE': str(Path(self.tmp.name) / 'queue'),
               'DIBS_ATLAS_HINTS': str(Path(self.tmp.name) / 'hints'),
               'ATLAS_RECONCILE_LOCK': str(Path(self.tmp.name) / 'reconcile.lock')}
        if profile is not None:
            env['ATLAS_CLAUDE_PROFILE'] = profile
        if threshold is not None:
            env['ATLAS_QUOTA_MAX'] = threshold
        patcher = mock.patch.dict(os.environ, {**os.environ, **env}, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        if profile is None:
            os.environ.pop('ATLAS_CLAUDE_PROFILE', None)
        if threshold is None:
            os.environ.pop('ATLAS_QUOTA_MAX', None)
        loader = importlib.machinery.SourceFileLoader('quota_ar', str(SCRIPT))
        module = importlib.util.module_from_spec(importlib.util.spec_from_loader('quota_ar', loader))
        loader.exec_module(module)
        claims = mock.patch.object(module, 'reconciler_claims', create=True)
        claims.start()
        self.addCleanup(claims.stop)
        return module

    @staticmethod
    def captured(ts):
        return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).isoformat()

    def usage(self, session=10, week=20, age=0, profile='personal'):
        return {'agents': {'claude': {'profiles': {profile: {'ok': True, 'quota': {
            'session': {'pct': session}, 'week_all': {'pct': week},
            'captured_at': self.captured(NOW - age)}}}}}}

    def quota(self, module, data, code=0):
        result = mock.Mock(returncode=code, stdout=json.dumps(data), stderr='')
        with mock.patch.object(module.subprocess, 'run', return_value=result), \
                mock.patch.object(module.time, 'time', return_value=NOW):
            return module.quota_pct()

    def test_session_and_weekly_max_and_boundaries(self):
        module = self.load()
        for session, week, expected in [(0, 0, 0), (70, 5, 70), (5, 95, 95), (100, 0, 100), (12.5, 20.8, 20.8)]:
            with self.subTest(session=session, week=week):
                self.assertEqual(self.quota(module, self.usage(session, week)), expected)

    def test_configured_profile_controls_usage_and_launch(self):
        module = self.load('work')
        self.assertEqual(self.quota(module, self.usage(5, 73, profile='work')), 73)
        result = mock.Mock(returncode=0, stdout='{"session": "example"}', stderr='')
        with mock.patch.object(module.subprocess, 'run', return_value=result) as launch, \
                mock.patch.object(module, 'stop_session'):
            module.refresh('/r', 'core')
        args = launch.call_args.args[0]
        self.assertEqual(args[args.index('--profile') + 1], 'work')

    def test_default_profile_is_explicit_in_launch(self):
        module = self.load()
        result = mock.Mock(returncode=0, stdout='{}', stderr='')
        with mock.patch.object(module.subprocess, 'run', return_value=result) as launch:
            module.refresh('/r', 'core')
        args = launch.call_args.args[0]
        self.assertEqual(args[args.index('--profile') + 1], 'personal')

    def test_invalid_missing_stale_and_future_usage_defers(self):
        module = self.load()
        cases = [({}, 0), (self.usage(age=3601), 0), (self.usage(age=-1), 0),
                 (self.usage(-1, 0), 0), (self.usage(0, 101), 0),
                 (self.usage('bad', 0), 0), (self.usage(None, 0), 0),
                 (self.usage(True, 0), 0), (self.usage(), 1)]
        for data, code in cases:
            with self.subTest(data=data, code=code):
                self.assertEqual(self.quota(module, data, code), 100)
        data = self.usage()
        del data['agents']['claude']['profiles']['personal']['quota']['week_all']
        self.assertEqual(self.quota(module, data), 100)
        data = self.usage()
        data['agents']['claude']['profiles']['personal']['quota']['captured_at'] = 'bad'
        self.assertEqual(self.quota(module, data), 100)
        self.assertEqual(self.quota(module, self.usage(age=3600)), 20)

    def test_malformed_response_and_launch_error_defer(self):
        module = self.load()
        with mock.patch.object(module.subprocess, 'run', return_value=mock.Mock(returncode=0, stdout='not json')):
            self.assertEqual(module.quota_pct(), 100)
        with mock.patch.object(module.subprocess, 'run', side_effect=OSError('unavailable')):
            self.assertEqual(module.quota_pct(), 100)

    def test_unknown_quota_never_launches_even_with_threshold_100(self):
        module = self.load()
        for threshold in (100, 101):
            with self.subTest(threshold=threshold):
                if os.path.exists(module.QUEUE):
                    os.remove(module.QUEUE)
                with mock.patch.object(module, 'QUOTA_MAX', threshold), \
                        mock.patch.object(module, 'quota_pct', return_value=100), \
                        mock.patch.object(module, 'own_commits_only', return_value=True), \
                        mock.patch.object(module.subprocess, 'run', return_value=mock.Mock(stdout='head\n')), \
                        mock.patch.object(module.subprocess, 'Popen') as launch:
                    module.queue(self.tmp.name)
                    launch.assert_not_called()
                with mock.patch.object(module, 'QUOTA_MAX', threshold), \
                        mock.patch.object(module, 'quota_pct', return_value=100), \
                        mock.patch.object(module, 'refresh') as refresh, \
                        mock.patch.object(module, 'sync_hints'):
                    module.run(nightly=False)
                    refresh.assert_not_called()
                self.assertEqual([q['repo'] for q in module.read_jsonl(module.QUEUE)], [self.tmp.name])

    def test_quota_is_rechecked_before_each_subsystem_launch(self):
        module = self.load()
        module.append_jsonl(module.QUEUE, {'ts': 1, 'repo': '/r', 'head': 'h'})
        calls = []
        def refresh(repo, subsystem):
            calls.append(subsystem)
            return True
        def quota():
            return 10 if not calls else 100
        before = (7, {'core': ['src/'], 'ui': ['ui/']}, ['core', 'ui'])
        after = (7, {'core': ['src/'], 'ui': ['ui/']}, ['ui'])
        with mock.patch.object(module, 'quota_pct', side_effect=quota), \
                mock.patch.object(module, 'stale_subsystems', side_effect=[before, after, after]), \
                mock.patch.object(module, 'refresh', side_effect=refresh), \
                mock.patch.object(module, 'sync_hints'):
            module.run(nightly=False)
        self.assertEqual(calls, ['core'])
        self.assertEqual([q['repo'] for q in module.read_jsonl(module.QUEUE)], ['/r'])
        self.assertEqual(module.read_jsonl(module.HINTS)[0]['refreshed'], ['core'])

    def test_malformed_threshold_still_enqueues_without_launching(self):
        module = self.load(threshold='invalid')
        with mock.patch.object(module, 'quota_pct', return_value=0), \
                mock.patch.object(module, 'own_commits_only', return_value=True), \
                mock.patch.object(module.subprocess, 'run', return_value=mock.Mock(stdout='head\n')), \
                mock.patch.object(module.subprocess, 'Popen') as launch:
            module.queue(self.tmp.name)
            launch.assert_not_called()
        self.assertEqual([q['repo'] for q in module.read_jsonl(module.QUEUE)], [self.tmp.name])


if __name__ == '__main__':
    unittest.main()
