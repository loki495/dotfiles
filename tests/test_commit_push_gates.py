"""ai/hooks/commit-gate.sh and push-guard.sh against fixture git repos and a fake Dibs CLI."""
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest

HOOKS = Path(__file__).resolve().parents[1] / 'ai' / 'hooks'

FAKE = '''#!/usr/bin/env python3
import json, os, sys
if os.environ.get("FAKE_DOWN"):
    sys.exit(1)
a = sys.argv[1:]
body = "Repo: %s\\nBranch: main\\nVerified at: %s\\n" % (os.environ["FAKE_REPO"], os.environ["FAKE_STAMP"])
sub = "subsystem: core\\nverified-at: %s\\nowned_paths: src/, app.py\\n" % os.environ["FAKE_STAMP"]
if a[0] == "todo:agent:list":
    print(json.dumps({"tasks": [{"id": 9, "state": "OPEN", "labels": ["feature atlas"]}]}))
else:
    print(json.dumps({"id": 9, "body": body, "comments": {"items": [{"body": sub}]}}))
'''


def git(repo, *args):
    return subprocess.run(['git', '-C', repo, '-c', 'user.name=t', '-c', 'user.email=t@t', *args],
                          check=True, capture_output=True, text=True).stdout.strip()


class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        t = Path(self.tmp.name)
        self.repo = str(t / 'repo')
        os.makedirs(self.repo)
        git(self.repo, 'init', '-q', '-b', 'main')
        for f in ('src/a.py', 'README.md'):
            Path(self.repo, f).parent.mkdir(exist_ok=True)
            Path(self.repo, f).write_text('0')
        git(self.repo, 'add', '.')
        git(self.repo, 'commit', '-qm', 'base')
        self.base = git(self.repo, 'rev-parse', 'HEAD')
        fake = t / 'fake-dibs'
        fake.write_text(FAKE)
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
        self.env = {**os.environ, 'DIBS_CMD': str(fake), 'FAKE_REPO': self.repo, 'FAKE_STAMP': self.base,
                    'XDG_RUNTIME_DIR': str(t)}

    def hook(self, name, command, **env):
        payload = {'cwd': self.repo, 'tool_input': {'command': command}}
        p = subprocess.run([str(HOOKS / name)], input=json.dumps(payload), capture_output=True, text=True,
                           env={**self.env, **env})
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(p.stdout)['hookSpecificOutput'] if p.stdout.strip() else None

    def change(self, path, stage=True):
        Path(self.repo, path).parent.mkdir(exist_ok=True)
        Path(self.repo, path).write_text('changed')
        if stage:
            git(self.repo, 'add', path)

    # commit gate
    def test_false_docs_claim_is_denied(self):
        self.change('src/a.py')
        o = self.hook('commit-gate.sh', 'git commit -m "x\n\nDocs: updated"')
        self.assertEqual(o['permissionDecision'], 'deny')
        self.assertIn('no documentation file', o['permissionDecisionReason'])

    def test_prose_docs_claim_without_doc_files_is_denied(self):
        self.change('src/a.py')
        for msg in ('Fix parser; README updated', 'Updated the docs for the parser', 'docs were updated'):
            o = self.hook('commit-gate.sh', f'git commit -m "{msg}"')
            self.assertEqual(o['permissionDecision'], 'deny', msg)

    def test_test_file_alone_does_not_back_a_docs_claim(self):
        self.change('src/a.py'); self.change('tests/test_a.py')
        o = self.hook('commit-gate.sh', 'git commit -m "Fix parser\n\nDocs: updated"')
        self.assertEqual(o['permissionDecision'], 'deny')
        self.assertIn('no documentation file', o['permissionDecisionReason'])

    def test_unrelated_wording_is_not_a_docs_claim(self):
        self.change('src/a.py')
        o = self.hook('commit-gate.sh', 'git commit -m "Fix parser, updated lockfile"')
        self.assertNotIn('permissionDecision', o)

    def test_true_docs_claim_passes_and_atlas_touch_is_noted(self):
        self.change('src/a.py'); self.change('README.md')
        o = self.hook('commit-gate.sh', 'git commit -m "x\n\nDocs: updated"')
        self.assertNotIn('permissionDecision', o)
        self.assertIn('touches feature-atlas subsystems: core', o['additionalContext'])
        self.assertNotIn('No doc or test file', o['additionalContext'])

    def test_code_only_commit_is_reminded_not_blocked(self):
        self.change('src/a.py')
        o = self.hook('commit-gate.sh', 'git commit -m "x"')
        self.assertIn('No doc or test file', o['additionalContext'])

    def test_docs_only_diff_outside_owned_paths_is_silent(self):
        self.change('README.md')
        self.assertIsNone(self.hook('commit-gate.sh', 'git commit -m "x"'))

    def test_dibs_down_drops_only_the_atlas_note(self):
        self.change('src/a.py'); self.change('README.md')
        self.assertIsNone(self.hook('commit-gate.sh', 'git commit -m "x"', FAKE_DOWN='1'))

    def test_non_commit_command_is_ignored(self):
        self.assertIsNone(self.hook('commit-gate.sh', 'git status'))

    # push gate
    def commit(self, path):
        self.change(path)
        git(self.repo, 'commit', '-qm', 'c')

    def test_push_with_stale_stamp_is_denied(self):
        self.commit('src/a.py')
        o = self.hook('push-guard.sh', 'git push origin main')
        self.assertEqual(o['permissionDecision'], 'deny')
        self.assertIn('core (1 owned file(s) changed', o['permissionDecisionReason'])

    def test_push_after_restamp_asks_as_before(self):
        self.commit('src/a.py')
        o = self.hook('push-guard.sh', 'git push origin main', FAKE_STAMP=git(self.repo, 'rev-parse', 'HEAD'))
        self.assertEqual(o['permissionDecision'], 'ask')

    def test_push_with_stamp_at_a_rewritten_sha_is_denied(self):
        self.commit('src/a.py')
        o = self.hook('push-guard.sh', 'git push origin main', FAKE_STAMP='deadbeef' * 5)
        self.assertEqual(o['permissionDecision'], 'deny')

    def test_push_after_docs_only_commit_asks(self):
        self.commit('README.md')
        self.assertEqual(self.hook('push-guard.sh', 'git push origin main')['permissionDecision'], 'ask')

    def test_push_with_dibs_down_still_asks(self):
        self.commit('src/a.py')
        o = self.hook('push-guard.sh', 'git push origin main', FAKE_DOWN='1')
        self.assertEqual(o['permissionDecision'], 'ask')

    def test_bad_stamp_never_reaches_git_and_symlinked_cache_is_ignored(self):
        self.commit('src/a.py')
        o = self.hook('push-guard.sh', 'git push origin main', FAKE_STAMP='--output=/tmp/x')
        self.assertEqual(o['permissionDecision'], 'ask')
        for f in Path(self.env['XDG_RUNTIME_DIR']).glob('atlas-*.json'):
            f.unlink()
            f.symlink_to('/etc/passwd')
        o = self.hook('push-guard.sh', 'git push origin main')
        self.assertEqual(o['permissionDecision'], 'deny')

    def test_non_push_is_ignored(self):
        self.assertIsNone(self.hook('push-guard.sh', 'git log'))


if __name__ == '__main__':
    unittest.main()
