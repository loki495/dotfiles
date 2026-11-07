"""Fail closed when atlas ownership or git coverage cannot be verified."""
import contextlib
import io
import json
import os
from pathlib import Path
import runpy
import subprocess
import tempfile
import unittest
from unittest import mock


HELPER = Path(__file__).resolve().parents[1] / 'ai' / 'hooks' / 'atlas-helper.py'


class AtlasHelperVerificationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = self.temp.name

    def run_helper(self, body, diff_code=0, page=1, last_page=1, withheld=False):
        def run(args, **kwargs):
            if args[0] == 'fake-dibs':
                if args[1:] == ['todo:agent:list', '--knowledge']:
                    result = {'tasks': [{'id': 7, 'state': 'OPEN', 'labels': ['feature atlas']}]}
                else:
                    result = {'id': 7, 'body': f'Repo: {self.repo}\nBranch: master\nVerified at: abcdef0\n',
                              'comments': {'items': [] if body is None else [{'body': body, 'withheld': withheld}],
                                           'page': page, 'lastPage': last_page}}
                return mock.Mock(returncode=0, stdout=json.dumps(result), stderr='')
            if args[0] == 'git':
                if 'symbolic-ref' in args:
                    return mock.Mock(returncode=0, stdout='master\n')
                if 'merge-base' in args:
                    return mock.Mock(returncode=0, stdout='')
                if 'diff' in args:
                    return mock.Mock(returncode=diff_code, stdout='')
            raise AssertionError(args)

        output = io.StringIO()
        with mock.patch.dict(os.environ, {'DIBS_CMD': 'fake-dibs', 'XDG_RUNTIME_DIR': self.repo,
                                         'ATLAS_CACHE_TTL': '0'}), \
                mock.patch('sys.argv', [str(HELPER), 'stale', self.repo]), \
                mock.patch('subprocess.run', side_effect=run), contextlib.redirect_stdout(output):
            try:
                runpy.run_path(str(HELPER), run_name='__main__')
            except RuntimeError:
                return {'error': 'helper failed'}
        return json.loads(output.getvalue())

    def assert_unverifiable(self, result):
        self.assertTrue('error' in result or 'skipped' in result or not result.get('atlas'), result)

    def test_git_diff_failure_is_not_reported_as_current(self):
        result = self.run_helper('subsystem: core\nverified-at: abcdef0\nowned_paths: src/\n', diff_code=128)
        self.assert_unverifiable(result)

    def test_valid_unchanged_subsystem_can_be_verified(self):
        result = self.run_helper('subsystem: core\nverified-at: abcdef0\nowned_paths: src/\n')
        self.assertEqual(result['subsystems'], [{'id': 'core', 'owned': ['src/']}])
        self.assertEqual(result['stale'], [])

    def test_malformed_subsystem_records_are_not_silently_omitted(self):
        for body in ('subsystem: core\nowned_paths: src/\n',
                     'subsystem: core\nverified-at: abcdef0\n',
                     'subsystem: core\nverified-at: abcdef0\nowned_paths: ,\n',
                     'subsystem:\nverified-at: abcdef0\nowned_paths: src/\n'):
            with self.subTest(body=body):
                self.assert_unverifiable(self.run_helper(body))

    def test_empty_subsystem_inventory_is_unverifiable(self):
        self.assert_unverifiable(self.run_helper(None))

    def test_truncated_atlas_comments_are_unverifiable(self):
        body = 'subsystem: core\nverified-at: abcdef0\nowned_paths: src/\n'
        self.assert_unverifiable(self.run_helper(body, page=1, last_page=2))

    def test_withheld_atlas_comment_makes_ownership_unverifiable(self):
        body = 'subsystem: core\nverified-at: abcdef0\nowned_paths: src/\n'
        self.assert_unverifiable(self.run_helper(body, withheld=True))

    def test_git_glob_pathspec_detects_changed_owned_file(self):
        def git(*args):
            return subprocess.run(['git', '-C', self.repo, *args], check=True,
                                  capture_output=True, text=True).stdout.strip()
        git('init', '-q', '-b', 'master')
        git('config', 'user.name', 'Test')
        git('config', 'user.email', 'test@example.invalid')
        test_dir = Path(self.repo) / 'tests'
        test_dir.mkdir()
        (test_dir / 'a.py').write_text('old\n')
        git('add', 'tests/a.py')
        git('commit', '-qm', 'initial')
        stamp = git('rev-parse', 'HEAD')
        (test_dir / 'a.py').write_text('new\n')
        git('commit', '-qam', 'changed')
        original_run = subprocess.run
        def run(args, **kwargs):
            if args[0] != 'fake-dibs':
                return original_run(args, **kwargs)
            if args[1:] == ['todo:agent:list', '--knowledge']:
                data = {'tasks': [{'id': 7, 'state': 'OPEN', 'labels': ['feature atlas']}]}
            else:
                data = {'id': 7, 'body': f'Repo: {self.repo}\nBranch: master\nVerified at: {stamp}\n',
                        'comments': {'items': [{'body': f'subsystem: core\nverified-at: {stamp}\nowned_paths: {pathspec}\n'}],
                                     'page': 1, 'lastPage': 1}}
            return mock.Mock(returncode=0, stdout=json.dumps(data), stderr='')
        for pathspec in (':(glob)tests/**', ':(bogus)tests/**'):
            with self.subTest(pathspec=pathspec):
                output = io.StringIO()
                with mock.patch.dict(os.environ, {'DIBS_CMD': 'fake-dibs', 'XDG_RUNTIME_DIR': self.repo,
                                                 'ATLAS_CACHE_TTL': '0'}), \
                        mock.patch('sys.argv', [str(HELPER), 'stale', self.repo]), \
                        mock.patch('subprocess.run', side_effect=run), contextlib.redirect_stdout(output):
                    try:
                        runpy.run_path(str(HELPER), run_name='__main__')
                    except RuntimeError:
                        result = {'error': 'helper failed'}
                    else:
                        result = json.loads(output.getvalue())
                if pathspec.startswith(':(bogus)'):
                    self.assert_unverifiable(result)
                else:
                    self.assertIn('core', [item['id'] for item in result['stale']])

    def test_touched_git_glob_matches_tracked_deleted_and_untracked_files(self):
        def git(*args):
            return subprocess.run(['git', '-C', self.repo, *args], check=True,
                                  capture_output=True, text=True).stdout.strip()
        git('init', '-q', '-b', 'master')
        git('config', 'user.name', 'Test')
        git('config', 'user.email', 'test@example.invalid')
        test_dir = Path(self.repo) / 'tests'
        test_dir.mkdir()
        for name in ('tracked.py', 'deleted.py'):
            (test_dir / name).write_text('content\n')
        git('add', 'tests')
        git('commit', '-qm', 'initial')
        stamp = git('rev-parse', 'HEAD')
        (test_dir / 'deleted.py').unlink()
        (test_dir / 'untracked.py').write_text('new\n')
        original_run = subprocess.run
        fail_git = False
        def run(args, **kwargs):
            if args[0] == 'git':
                if fail_git:
                    return mock.Mock(returncode=128, stdout='', stderr='git failed')
                return original_run(args, **kwargs)
            if args[0] == 'fake-dibs':
                if args[1:] == ['todo:agent:list', '--knowledge']:
                    data = {'tasks': [{'id': 7, 'state': 'OPEN', 'labels': ['feature atlas']}]}
                else:
                    body = f'subsystem: core\nverified-at: {stamp}\nowned_paths: :(glob)tests/**\n'
                    plain = f'subsystem: plain\nverified-at: {stamp}\nowned_paths: tests/**\n'
                    data = {'id': 7, 'body': f'Repo: {self.repo}\nBranch: master\nVerified at: {stamp}\n',
                            'comments': {'items': [{'body': body}, {'body': plain}], 'page': 1, 'lastPage': 1}}
                return mock.Mock(returncode=0, stdout=json.dumps(data), stderr='')
            raise AssertionError(args)
        def touched(filename):
            output = io.StringIO()
            with mock.patch.dict(os.environ, {'DIBS_CMD': 'fake-dibs', 'XDG_RUNTIME_DIR': self.repo,
                                             'ATLAS_CACHE_TTL': '0'}), \
                    mock.patch('sys.argv', [str(HELPER), 'touched', self.repo, filename]), \
                    mock.patch('subprocess.run', side_effect=run), contextlib.redirect_stdout(output):
                try:
                    runpy.run_path(str(HELPER), run_name='__main__')
                except RuntimeError:
                    return {'error': 'helper failed'}
            return json.loads(output.getvalue())
        for filename in ('tests/tracked.py', 'tests/deleted.py', 'tests/untracked.py'):
            with self.subTest(filename=filename):
                self.assertCountEqual(touched(filename)['subsystems'], ['core', 'plain'])
        git('add', '-u')
        git('mv', 'tests/tracked.py', 'tests/moved.py')
        for filename in ('tests/deleted.py', 'tests/tracked.py', 'tests/moved.py'):
            with self.subTest(staged=filename):
                self.assertCountEqual(touched(filename)['subsystems'], ['core', 'plain'])
        fail_git = True
        self.assert_unverifiable(touched('tests/tracked.py'))


if __name__ == '__main__':
    unittest.main()
