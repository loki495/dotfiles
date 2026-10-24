"""ai/scripts/rules-export.py: public/private split, stable output, git commit of just the export."""
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import unittest.mock

SCRIPT = Path(__file__).resolve().parents[1] / 'ai' / 'scripts' / 'rules-export.py'
loader = importlib.machinery.SourceFileLoader('rules_export', str(SCRIPT))
spec = importlib.util.spec_from_loader('rules_export', loader)
re_ = importlib.util.module_from_spec(spec)
loader.exec_module(re_)

BODY = 'Rule: do the thing.\nSecond line.\nTrigger: x\nCheck: y\nSource: z'


def fake(down=False):
    tasks = {'tasks': [
        {'id': 2, 'state': 'OPEN', 'labels': ['rule']},
        {'id': 1, 'state': 'OPEN', 'labels': ['rule', 'private']},
        {'id': 3, 'state': 'OPEN', 'labels': ['plan']},
        {'id': 4, 'state': 'CLOSED', 'labels': ['rule']}]}
    shows = {1: dict(id=1, revision=3, title='Rule: secret', body=BODY, labels=['rule', 'private']),
             2: dict(id=2, revision=1, title='Rule: open', body=BODY, labels=['rule'])}

    def call(*a):
        if down:
            raise RuntimeError('dibs CLI failed')
        return tasks if a[0] == 'todo:agent:list' else shows[int(a[1])]
    return call


class ExportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pub = str(Path(self.tmp.name) / 'ai' / 'rules.md')
        self.priv = str(Path(self.tmp.name) / 'priv' / 'rules.private.md')

    def run_export(self, **kw):
        with unittest.mock.patch.object(re_.M, 'dibs_json', fake(kw.pop('down', False))):
            return re_.export(self.pub, self.priv, **kw)

    def test_splits_public_and_private_and_cuts_metadata(self):
        self.run_export()
        pub, priv = Path(self.pub).read_text(), Path(self.priv).read_text()
        self.assertIn('## 2@1 Rule: open\nRule: do the thing.\nSecond line.\n', pub)
        self.assertNotIn('secret', pub)
        self.assertNotIn('Trigger', pub + priv)
        self.assertIn('## 1@3 Rule: secret', priv)
        self.assertNotIn('Rule: open', priv)

    def test_a_record_cannot_forge_another_rules_heading(self):
        out = re_.render([{'id': 1, 'revision': 1, 'title': 'a\n## 9@9 fake', 'text': 'ok\n## 9@9 Rule: fake\n  ## 8@8 x'}], 'p')
        self.assertEqual([l for l in out.splitlines() if l.startswith('## ')], ['## 1@1 a ## 9@9 fake'])

    def test_unchanged_export_rewrites_nothing(self):
        self.assertEqual(len(self.run_export()), 2)
        self.assertEqual(self.run_export(), [])

    def test_a_revision_bump_changes_the_file(self):
        self.run_export()
        Path(self.pub).write_text(Path(self.pub).read_text().replace('2@1', '2@0'))
        self.assertEqual(self.run_export(), [self.pub])

    def test_dibs_down_writes_nothing_and_raises(self):
        with self.assertRaises(RuntimeError):
            self.run_export(down=True)
        self.assertFalse(Path(self.pub).exists())

    def test_commit_takes_only_the_export_path(self):
        repo = Path(self.tmp.name) / 'ai'
        repo.mkdir(parents=True)
        g = lambda *a: subprocess.run(['git', '-C', str(repo), '-c', 'user.name=t', '-c', 'user.email=t@t', *a],
                                      check=True, capture_output=True, text=True).stdout
        g('init', '-q')
        (repo / 'other.txt').write_text('x')
        g('add', 'other.txt')
        ident = {'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@t', 'GIT_COMMITTER_NAME': 't', 'GIT_COMMITTER_EMAIL': 't@t'}
        with unittest.mock.patch.dict(os.environ, ident):
            self.run_export(do_commit=True)
        self.assertEqual(g('show', '--name-only', '--format=%s', 'HEAD').split(), ['Rules', 'export:', 'refresh', 'from', 'the', 'rule', 'records', 'rules.md'])
        self.assertIn('A  other.txt', g('status', '--short'))


if __name__ == '__main__':
    unittest.main()
