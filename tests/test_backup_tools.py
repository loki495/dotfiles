"""backup-tools/common-git must not commit on a remote site unless AUTO_COMMIT_REMOTE=true."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

COMMON_GIT = Path(__file__).resolve().parents[1] / 'backup-tools' / 'common-git'


class GitCommitGateTests(unittest.TestCase):
    def run_git_commit(self, auto_commit):
        with tempfile.TemporaryDirectory(prefix='backup-tools-tests-') as temp:
            ssh_log = Path(temp) / 'ssh.log'
            stub = Path(temp) / 'ssh'
            stub.write_text(f'#!/bin/sh\necho "$*" >> {ssh_log}\n')
            stub.chmod(0o755)
            script = ('echo_info() { :; }\n'
                      'run_ssh() { echo " M site/index.php"; }\n'
                      f'source {COMMON_GIT}\n'
                      'git_commit\n')
            env = dict(os.environ, PATH=f'{temp}:/usr/bin:/bin', BACKUP_TOOLS_CONF_LOADED='1',
                       AUTO_COMMIT_REMOTE=auto_commit)
            result = subprocess.run(['bash', '-c', script], env=env, capture_output=True, text=True)
            return result, ssh_log.read_text() if ssh_log.exists() else ''

    def test_dirty_remote_is_not_committed_by_default(self):
        result, ssh_calls = self.run_git_commit('')
        self.assertEqual(result.returncode, 1)
        self.assertIn('AUTO_COMMIT_REMOTE=true', result.stderr)
        self.assertNotIn('commit -m', ssh_calls)

    def test_other_values_do_not_opt_in(self):
        result, ssh_calls = self.run_git_commit('yes')
        self.assertEqual(result.returncode, 1)
        self.assertNotIn('commit -m', ssh_calls)

    def test_dirty_remote_is_committed_when_opted_in(self):
        result, ssh_calls = self.run_git_commit('true')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('add .', ssh_calls)
        self.assertIn('commit -m', ssh_calls)


if __name__ == '__main__':
    unittest.main(verbosity=2)
