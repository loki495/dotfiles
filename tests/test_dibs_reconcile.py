"""ai/scripts/dibs-reconcile.py against a fixture git repo and a fake Dibs."""
import importlib.machinery
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import unittest.mock
from contextlib import redirect_stderr

SCRIPT = Path(__file__).resolve().parents[1] / 'ai' / 'scripts' / 'dibs-reconcile.py'
loader = importlib.machinery.SourceFileLoader('dibs_reconcile', str(SCRIPT))
spec = importlib.util.spec_from_loader('dibs_reconcile', loader)
dr = importlib.util.module_from_spec(spec)
loader.exec_module(dr)


def git(repo, *args):
    p = subprocess.run(['git', '-C', repo, '-c', 'user.name=t', '-c', 'user.email=t@t', *args],
                       check=True, capture_output=True, text=True)
    return p.stdout.strip()


class FakeDibs:
    """Answers the todo:agent:* calls the reconciler makes and records the writes."""

    def __init__(self, atlas_body, standing=None, children=()):
        self.atlas_body, self.standing, self.children = atlas_body, standing, list(children)
        self.writes, self.down = [], False

    def __call__(self, *a):
        if self.down:
            raise RuntimeError('dibs CLI failed')
        cmd, args = a[0], a[1:]
        if cmd == 'todo:agent:list':
            tasks = [{'id': 9, 'title': 'Feature atlas: T', 'state': 'OPEN', 'labels': ['feature atlas']}]
            if '--knowledge' not in args:
                tasks = [{'id': 5, 'title': 'p', 'state': 'OPEN', 'labels': ['plan']}]
                if self.standing:
                    tasks.append({'id': 50, 'title': dr.STANDING_TITLE, 'state': 'OPEN', 'labels': []})
            return {'tasks': tasks}
        if cmd == 'todo:agent:show':
            i = int(args[0])
            if i == 9:
                return {'id': 9, 'title': 'Feature atlas: T', 'body': self.atlas_body}
            if i == 5:
                return {'id': 5, 'body': 'S1 done', 'state': 'OPEN', 'children': [
                    {'id': 6, 'title': 'S1 a', 'state': 'CLOSED'}, {'id': 7, 'title': 'S2 b', 'state': 'CLOSED'}]}
            if i in (6, 7):
                return {'id': i, 'closing': {'closedAt': '2026-10-25T00:00:00+00:00',
                                              'result': {'commit': 'abcdef1'} if i == 6 else {}}}
            if i == 50:
                return {'id': 50, 'revision': 1, 'body': self.standing,
                        'children': [{'id': c, 'state': 'OPEN'} for c, _ in self.children]}
            return {'id': i, 'body': dict(self.children)[i]}
        if cmd == 'todo:agent:claim':
            self.writes.append(a)
            return {'capabilityToken': 'tok'}
        self.writes.append(a)
        return {'id': 50}


class ReconcileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = self.tmp.name
        git(self.repo, 'init', '-q', '-b', 'main')
        for n in range(4):
            Path(self.repo, 'f').write_text(str(n))
            git(self.repo, 'add', 'f')
            git(self.repo, 'commit', '-qm', str(n))
        self.first = git(self.repo, 'rev-list', '--max-parents=0', 'HEAD')
        self.orig = dr.M.dibs_json
        self.addCleanup(lambda: setattr(dr.M, 'dibs_json', self.orig))
        self.addCleanup(self.tmp.cleanup)

    def atlas(self, sha):
        return f'Repo: {self.repo}\nBranch: main\nVerified at: {sha}\n'

    def run_with(self, fake, **kw):
        dr.M.dibs_json = fake
        dr.reconcile(out=lambda *_: None, **kw)

    def test_violation_creates_standing_issue_and_task(self):
        fake = FakeDibs(self.atlas(self.first))
        self.run_with(fake)
        cmds = [w[0] for w in fake.writes]
        self.assertEqual(cmds.count('todo:agent:create'), 2)
        key = f'reconciler:atlas:T:{self.first[:9]}'
        self.assertIn(key, [w for c in fake.writes for w in c])

    def test_second_run_files_nothing(self):
        fake = FakeDibs(self.atlas(self.first))
        self.run_with(fake)
        body = dr.render(dr.atlas_findings([{'title': 'Feature atlas: T', 'body': fake.atlas_body}], 3),
                         [], dr.plan_findings(dr.gather()[2]))
        key = f'reconciler:atlas:T:{self.first[:9]}'
        again = FakeDibs(fake.atlas_body, standing=body, children=[(60, f'Key: {key}\nx')])
        self.run_with(again)
        self.assertEqual(again.writes, [])

    def test_cleared_violation_closes_its_task(self):
        head = git(self.repo, 'rev-parse', 'HEAD')
        fake = FakeDibs(self.atlas(head), standing='old', children=[(60, 'Key: reconciler:atlas:T:gone\nx')])
        self.run_with(fake)
        cmds = [w[0] for w in fake.writes]
        self.assertEqual(cmds, ['todo:agent:update', 'todo:agent:claim', 'todo:agent:complete'])

    def test_cap_keeps_violations_out_of_tasks_but_in_the_standing_issue(self):
        fake = FakeDibs(self.atlas(self.first))
        self.run_with(fake, max_tasks=0)
        creates = [w for w in fake.writes if w[0] == 'todo:agent:create']
        self.assertEqual(len(creates), 1)
        self.assertIn('1 more violations not filed as tasks (cap 0)', creates[0][creates[0].index('--body') + 1])

    def test_existing_task_keeps_its_slot_under_the_cap(self):
        key = f'reconciler:atlas:T:{self.first[:9]}'
        fake = FakeDibs(self.atlas(self.first), standing='old', children=[(60, f'Key: {key}\nx')])
        self.run_with(fake, max_tasks=1)
        self.assertEqual([w[0] for w in fake.writes], ['todo:agent:update'])

    def test_dry_run_writes_nothing(self):
        fake = FakeDibs(self.atlas(self.first))
        self.run_with(fake, dry_run=True)
        self.assertEqual(fake.writes, [])

    def test_dibs_unreachable_is_handled_and_writes_nothing(self):
        fake = FakeDibs(self.atlas(self.first))
        fake.down = True
        dr.M.dibs_json = fake
        err = io.StringIO()
        with redirect_stderr(err), unittest.mock.patch('sys.argv', ['x']):
            self.assertEqual(dr.main(), 2)
        self.assertIn('nothing written', err.getvalue())
        self.assertEqual(fake.writes, [])

    def test_plan_findings_flag_missing_status_and_sha(self):
        f = dr.plan_findings([(
            {'id': 5, 'body': 'S1 done', 'children': [{'id': 7, 'title': 'S2 b', 'state': 'CLOSED'}]},
            {7: {'closedAt': '2026-10-25', 'result': {}}})])
        self.assertEqual(len(f), 2)
        self.assertIn('not in the plan body', f[0])
        self.assertIn('without a commit SHA', f[1])


if __name__ == '__main__':
    import unittest.mock  # noqa: F401
    unittest.main()
