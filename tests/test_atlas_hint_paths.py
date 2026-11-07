"""Worktree hint identity and canonical subsystem matching."""
import importlib.machinery
import importlib.util
import contextlib
import builtins
import io
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / 'ai' / 'scripts' / 'atlas-refresh.py'


class AtlasHintPathsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.repo = self.path / 'repo'
        self.other = self.path / 'other'
        self.worktree = self.path / 'worktree'
        for repo in (self.repo, self.other):
            subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
            subprocess.run(['git', '-C', str(repo), 'config', 'user.name', 'Test'], check=True)
            subprocess.run(['git', '-C', str(repo), 'config', 'user.email', 'test@example.invalid'], check=True)
            (repo / 'file').write_text('content')
            subprocess.run(['git', '-C', str(repo), 'add', 'file'], check=True)
            subprocess.run(['git', '-C', str(repo), 'commit', '-qm', 'initial'], check=True)
        subprocess.run(['git', '-C', str(self.repo), 'worktree', 'add', '-qb', 'feature', str(self.worktree)], check=True)
        env = mock.patch.dict(os.environ, {'DIBS_ATLAS_HINTS': str(self.path / 'hints'),
                                           'ATLAS_QUEUE': str(self.path / 'queue'),
                                           'ATLAS_RECONCILE_LOCK': str(self.path / 'lock')})
        env.start()
        self.addCleanup(env.stop)
        loader = importlib.machinery.SourceFileLoader('hint_paths_ar', str(SCRIPT))
        self.ar = importlib.util.module_from_spec(importlib.util.spec_from_loader('hint_paths_ar', loader))
        loader.exec_module(self.ar)
        self.atlas = {'id': 7, 'revision': 1, 'title': 'Feature atlas: T', 'body': 'Intro\n',
                      'comments': {'items': [{'body': f'subsystem: {name}\n'} for name in
                                             ('ui-components', 'core-ui', 'core_ui')],
                                   'page': 1, 'lastPage': 1}}

    def sync(self, records):
        for record in records:
            self.ar.append_jsonl(self.ar.HINTS, record)
        with mock.patch.object(self.ar, 'atlas_parents', return_value=[(str(self.repo), self.atlas)]), \
                mock.patch.object(self.ar.DM, 'dibs_json') as update:
            self.ar.sync_hints()
        if update.call_count == 0:
            return self.atlas['body']
        self.assertEqual(update.call_count, 1)
        args = update.call_args.args
        return next(a[len('--body='):] for a in args if a.startswith('--body='))

    def hint(self, repo, name, ts):
        head = subprocess.run(['git', '-C', str(repo), 'rev-parse', 'HEAD'], check=True,
                              capture_output=True, text=True).stdout.strip()
        return {'repo': str(repo), 'subsystem': name, 'ts': ts, 'head': head, 'change': name}

    def test_linked_worktree_hint_is_visible_but_unrelated_repo_is_not(self):
        body = self.sync([self.hint(self.worktree, 'ui-components', 1), self.hint(self.other, 'other-only', 1)])
        self.assertIn('ui-components', body)
        self.assertNotIn('other-only', body)

    def test_aliases_clear_only_for_unambiguous_canonical_subsystem(self):
        records = [self.hint(self.worktree, 'UI Components', 1), self.hint(self.worktree, 'UI_Components', 1),
                   self.hint(self.worktree, 'UI-COMPONENTS', 1), self.hint(self.worktree, 'core ui', 1),
                   self.hint(self.worktree, 'mystery', 1), self.hint(self.worktree, 'core-ui', 1),
                   {'repo': str(self.repo), 'ts': 2, 'refreshed': ['ui-components', 'core-ui'],
                    'head': self.hint(self.repo, 'core-ui', 1)['head']}]
        body = self.sync(records)
        self.assertNotIn('UI Components', body)
        self.assertNotIn('UI_Components', body)
        self.assertNotIn('UI-COMPONENTS', body)
        self.assertNotIn('core-ui: core-ui', body)
        self.assertIn('core ui', body)
        self.assertIn('mystery', body)

    def test_worktree_hint_requires_verified_head_to_contain_worktree_commit(self):
        def git(repo, *args):
            return subprocess.run(['git', '-C', str(repo), *args], check=True,
                                  capture_output=True, text=True).stdout.strip()
        base = git(self.repo, 'rev-parse', 'HEAD')
        (self.worktree / 'feature').write_text('feature')
        git(self.worktree, 'add', 'feature')
        git(self.worktree, 'commit', '-qm', 'feature')
        feature = git(self.worktree, 'rev-parse', 'HEAD')
        hint = self.hint(self.worktree, 'ui-components', 1)
        hint['head'] = feature
        for marker in ({'repo': str(self.repo), 'ts': 2, 'refreshed': ['ui-components'], 'head': base},
                       {'repo': str(self.repo), 'ts': 2, 'refreshed': ['ui-components']}):
            with self.subTest(marker=marker):
                Path(self.ar.HINTS).unlink(missing_ok=True)
                body = self.sync([hint, marker])
                self.assertIn('ui-components', body)
        git(self.repo, 'merge', '--ff-only', 'feature')
        merged = git(self.repo, 'rev-parse', 'HEAD')
        Path(self.ar.HINTS).unlink(missing_ok=True)
        body = self.sync([hint, {'repo': str(self.repo), 'ts': 3, 'refreshed': ['ui-components'], 'head': merged}])
        self.assertNotIn('ui-components', body)

    def test_same_checkout_branch_switch_requires_hint_commit_ancestry(self):
        def git(*args):
            return subprocess.run(['git', '-C', str(self.repo), *args], check=True,
                                  capture_output=True, text=True).stdout.strip()
        base = git('rev-parse', 'HEAD')
        (self.repo / 'feature').write_text('feature')
        git('add', 'feature')
        git('commit', '-qm', 'feature')
        feature = git('rev-parse', 'HEAD')
        hint = self.hint(self.repo, 'ui-components', 1)
        self.assertEqual(hint['head'], feature)
        git('checkout', '-qb', 'other', base)
        for marker in ({'repo': str(self.repo), 'ts': 2, 'refreshed': ['ui-components'], 'head': base},
                       {'repo': str(self.repo), 'ts': 2, 'refreshed': ['ui-components']}):
            with self.subTest(marker=marker):
                Path(self.ar.HINTS).unlink(missing_ok=True)
                self.assertIn('ui-components', self.sync([hint, marker]))
        git('merge', '--ff-only', 'main')
        Path(self.ar.HINTS).unlink(missing_ok=True)
        body = self.sync([hint, {'repo': str(self.repo), 'ts': 3, 'refreshed': ['ui-components'], 'head': feature}])
        self.assertNotIn('ui-components', body)

    def test_incomplete_or_withheld_comments_leave_alias_raw_and_pending(self):
        original = self.atlas['comments']
        for comments in ({**original, 'lastPage': 2},
                         {**original, 'items': original['items'] + [{'body': '', 'withheld': True}]}):
            with self.subTest(comments=comments):
                Path(self.ar.HINTS).unlink(missing_ok=True)
                self.atlas['comments'] = comments
                hint = self.hint(self.repo, 'UI Components', 1)
                marker = {'repo': str(self.repo), 'ts': 2, 'refreshed': ['ui-components'], 'head': hint['head']}
                body = self.sync([hint, marker])
                self.assertIn('UI Components', body)

    def test_deleted_linked_worktree_does_not_erase_existing_pending_hint(self):
        body = self.sync([self.hint(self.worktree, 'ui-components', 1)])
        self.assertIn('ui-components', body)
        self.atlas['body'] = body
        subprocess.run(['git', '-C', str(self.repo), 'worktree', 'remove', str(self.worktree)], check=True)
        warning = io.StringIO()
        with mock.patch.object(self.ar, 'atlas_parents', return_value=[(str(self.repo), self.atlas)]), \
                mock.patch.object(self.ar.DM, 'dibs_json') as update, contextlib.redirect_stderr(warning):
            self.ar.sync_hints()
        if update.called:
            args = update.call_args.args
            new_body = next(a[len('--body='):] for a in args if a.startswith('--body='))
            self.assertIn('ui-components', new_body)
        else:
            self.assertIn(str(self.worktree), warning.getvalue())

    def test_unresolved_unrelated_repo_safely_skips_parent_update_with_warning(self):
        missing = self.path / 'unrelated-missing'
        unrelated = {'repo': str(missing), 'subsystem': 'unknown', 'ts': 1,
                     'head': 'a' * 40, 'change': 'not this repo'}
        self.ar.append_jsonl(self.ar.HINTS, unrelated)
        self.ar.append_jsonl(self.ar.HINTS, self.hint(self.repo, 'ui-components', 1))
        warning = io.StringIO()
        with mock.patch.object(self.ar, 'atlas_parents', return_value=[(str(self.repo), self.atlas)]), \
                mock.patch.object(self.ar.DM, 'dibs_json') as update, contextlib.redirect_stderr(warning):
            self.ar.sync_hints()
        update.assert_not_called()
        self.assertIn(str(missing), warning.getvalue())

    def test_missing_or_unreadable_queue_keeps_generated_block(self):
        self.atlas['body'] = ('Intro\n\n## Pending since last refresh\n'
                              '<!-- atlas-refresh:start -->\n- core: existing\n'
                              '<!-- atlas-refresh:end -->\n')
        original_open = builtins.open
        for unreadable in (False, True):
            with self.subTest(unreadable=unreadable):
                hint_path = Path(self.ar.HINTS)
                hint_path.unlink(missing_ok=True)
                if unreadable:
                    hint_path.write_text('')
                def open_file(path, *args, **kwargs):
                    if unreadable and str(path) == str(hint_path):
                        raise PermissionError('not readable')
                    return original_open(path, *args, **kwargs)
                with mock.patch.object(self.ar, 'atlas_parents', return_value=[(str(self.repo), self.atlas)]), \
                        mock.patch.object(self.ar.DM, 'dibs_json') as update, \
                        mock.patch('builtins.open', side_effect=open_file):
                    self.ar.sync_hints()
                update.assert_not_called()

    def test_readable_empty_queue_clears_only_generated_block(self):
        self.atlas['body'] = ('Intro\n\n## Pending since last refresh\n- manual\n'
                              '<!-- atlas-refresh:start -->\n- core: existing\n'
                              '<!-- atlas-refresh:end -->\n\n## Other\nkeep\n')
        Path(self.ar.HINTS).write_text('')
        body = self.sync([])
        self.assertIn('- manual\n', body)
        self.assertIn('## Other\nkeep\n', body)
        self.assertNotIn('- core: existing', body)
        self.assertNotIn('<!-- atlas-refresh:start -->', body)


if __name__ == '__main__':
    unittest.main()
