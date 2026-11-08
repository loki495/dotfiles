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

    def test_cross_subsystem_rename_sends_old_and_new_paths_to_atlas_helper(self):
        Path(self.repo, 'other').mkdir()
        git(self.repo, 'mv', 'src/a.py', 'other/a.py')
        helper = Path(self.tmp.name, 'record-helper')
        output = Path(self.tmp.name, 'helper-args.json')
        helper.write_text('#!/usr/bin/env python3\nimport json, os, sys\n'
                          'open(os.environ["HELPER_ARGS"], "w").write(json.dumps(sys.argv[1:]))\n'
                          'print(json.dumps({"subsystems": ["source", "target"]}))\n')
        helper.chmod(0o755)
        self.hook('commit-gate.sh', 'git commit -m "Move source"', HELPER=str(helper), HELPER_ARGS=str(output))
        args = json.loads(output.read_text())
        self.assertEqual(args[:2], ['touched', self.repo])
        self.assertCountEqual(args[2:], ['src/a.py', 'other/a.py'])

    # commit gate: rules 737, 738
    def test_dibs_reference_in_message_is_denied_with_rule_737(self):
        self.change('src/a.py'); self.change('README.md')
        for msg in ('Fix per Dibs 123', 'fix dibs task 5', 'DIBS plan #7', 'dibs id 9', 'dibs #12',
                    'closes todo_show 42', 'todo_claim 3', 'todo_complete 8'):
            o = self.hook('commit-gate.sh', f'git commit -m "{msg}"')
            self.assertEqual(o['permissionDecision'], 'deny', msg)
            self.assertIn('737', o['permissionDecisionReason'], msg)

    def test_dibs_reference_added_to_staged_markdown_is_denied(self):
        self.change('src/a.py')
        Path(self.repo, 'README.md').write_text('see Dibs task 77\n')
        git(self.repo, 'add', 'README.md')
        o = self.hook('commit-gate.sh', 'git commit -m "x"')
        self.assertEqual(o['permissionDecision'], 'deny')
        self.assertIn('737', o['permissionDecisionReason'])

    def test_dibs_reference_in_unstaged_or_non_markdown_file_is_not_denied(self):
        Path(self.repo, 'README.md').write_text('see Dibs task 77\n')
        self.change('src/a.py')
        Path(self.repo, 'src/b.py').write_text('# Dibs 5\n')
        git(self.repo, 'add', 'src/b.py')
        o = self.hook('commit-gate.sh', 'git commit -m "x"')
        self.assertTrue(o is None or 'permissionDecision' not in o)

    def test_claude_session_trailer_is_denied_with_rule_738(self):
        self.change('src/a.py')
        o = self.hook('commit-gate.sh', 'git commit -m "x\n\nClaude-Session: abc123"')
        self.assertEqual(o['permissionDecision'], 'deny')
        self.assertIn('738', o['permissionDecisionReason'])

    def test_clean_messages_mentioning_rules_or_dibs_are_not_denied(self):
        self.change('src/a.py')
        for msg in ('Rules 757 and 927: use todo_search', 'dibs-block hook fix', 'Dibs integration', 'fix 123 bugs'):
            o = self.hook('commit-gate.sh', f'git commit -m "{msg}"')
            self.assertTrue(o is None or 'permissionDecision' not in o, msg)

    # push gate
    def commit(self, path):
        self.change(path)
        git(self.repo, 'commit', '-qm', 'c')

    def test_push_with_stale_stamp_asks_and_names_the_stale_subsystem(self):
        self.commit('src/a.py')
        o = self.hook('push-guard.sh', 'git push origin main')
        self.assertEqual(o['permissionDecision'], 'ask')
        self.assertIn('Feature atlas stale for: core (1 owned file(s) changed', o['permissionDecisionReason'])

    def test_push_after_restamp_asks_as_before(self):
        self.commit('src/a.py')
        o = self.hook('push-guard.sh', 'git push origin main', FAKE_STAMP=git(self.repo, 'rev-parse', 'HEAD'))
        self.assertEqual(o['permissionDecision'], 'ask')

    def test_push_with_stamp_at_a_rewritten_sha_asks_with_the_stale_note(self):
        self.commit('src/a.py')
        o = self.hook('push-guard.sh', 'git push origin main', FAKE_STAMP='deadbeef' * 5)
        self.assertEqual(o['permissionDecision'], 'ask')
        self.assertIn('atlas stale', o['permissionDecisionReason'])

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
        self.assertEqual(o['permissionDecision'], 'ask')
        self.assertIn('atlas stale', o['permissionDecisionReason'])

    def push_setup(self, upstream=True):
        remote = str(Path(self.tmp.name) / 'remote.git')
        subprocess.run(['git', 'init', '-q', '--bare', '-b', 'main', remote], check=True)
        git(self.repo, 'remote', 'add', 'origin', remote)
        if upstream:
            git(self.repo, 'push', '-q', '-u', 'origin', 'main')
        git(self.repo, 'config', 'push.default', 'upstream')
        self.change('src/a.py'); git(self.repo, 'commit', '-qm', 'first unpushed')
        self.change('README.md'); git(self.repo, 'commit', '-qm', 'second unpushed')
        return git(self.repo, 'log', '--oneline', 'origin/main..HEAD') if upstream else ''

    def test_push_lists_unpushed_commits_in_reason_and_additional_context_every_time(self):
        log = self.push_setup()
        self.assertEqual(len(log.splitlines()), 2)
        for _ in range(2):
            o = self.hook('push-guard.sh', 'git push')
            self.assertEqual(o['permissionDecision'], 'ask')
            for field in ('permissionDecisionReason', 'additionalContext'):
                self.assertIn(log, o[field], field)
                self.assertIn('as of last fetch', o[field], field)
                self.assertNotIn('Risky flags:', o[field], field)

    def test_push_with_risky_flags_names_them(self):
        self.push_setup()
        o = self.hook('push-guard.sh', 'git push --force-with-lease --no-verify origin main')
        for field in ('permissionDecisionReason', 'additionalContext'):
            line = next(l for l in o[field].splitlines() if l.startswith('Risky flags:'))
            self.assertIn('--force-with-lease', line)
            self.assertIn('--no-verify', line)
        for cmd, flag in (('git push -f', '-f'), ('git push origin --delete old', '--delete'),
                          ('git push origin :old', ':old'), ('git push --mirror', '--mirror')):
            o = self.hook('push-guard.sh', cmd)
            line = next(l for l in o['permissionDecisionReason'].splitlines() if l.startswith('Risky flags:'))
            self.assertIn(flag, line, cmd)

    def test_push_without_upstream_says_unpushed_commits_are_unknown_and_asks(self):
        self.push_setup(upstream=False)
        o = self.hook('push-guard.sh', 'git push origin main')
        self.assertEqual(o['permissionDecision'], 'ask')
        for field in ('permissionDecisionReason', 'additionalContext'):
            self.assertIn('no upstream', o[field].lower(), field)

    def test_non_push_is_ignored(self):
        self.assertIsNone(self.hook('push-guard.sh', 'git log'))


if __name__ == '__main__':
    unittest.main()
