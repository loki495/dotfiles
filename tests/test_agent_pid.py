"""Process-level identity contract; no Claude service or Dibs database is used."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_dibs_block_hook import STUB, HOOK

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'ai/scripts/agent-pid.py'

# Invoked through a symlink named claude so the kernel exposes a realistic
# process name, with shells between the agent and its hook/resolver.
DRIVER = r'''
import json, os, subprocess, sys
from pathlib import Path
root, mode = sys.argv[1:]
env = os.environ.copy()
if mode == 'foreign': env['DIBS_AGENT_PID'] = env['FOREIGN_PID']
else: env.pop('DIBS_AGENT_PID', None)
if mode == 'hook':
    payload = json.dumps({'session_id':'same-session', 'cwd':root, 'prompt':'work on dibs 5'})
    p = subprocess.run(['bash', '-c', 'bash -c \'exec "$@"\' -- "$@"', '--', sys.executable, env['HOOK'], 'prompt'], input=payload, text=True, capture_output=True, env=env)
else:
    p = subprocess.run(['bash', '-c', 'bash -c \'"$1" "$2" --caller-pid $$\' -- "$@"', '--', sys.executable, env['HELPER']], text=True, capture_output=True, env=env)
print(json.dumps({'pid':os.getpid(), 'returncode':p.returncode, 'stdout':p.stdout, 'stderr':p.stderr}))
'''


# A tiny native stand-in preserves realistic argv (including the first Claude
# subcommand) while it waits for child wrappers to resolve their caller.
FAKE_CLAUDE = r'''
#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
int main(void) {
    fprintf(stderr, "agent-pid=%ld\n", (long)getpid());
    const char *service = getenv("FAKE_SERVICE");
    pid_t child = fork();
    if (child == 0) {
        if (service) {
            unsetenv("FAKE_SERVICE");
            execl("/bin/bash", "bash", "-c", "\"$FAKE_CLAUDE\" \"$1\" run; :", "--", service, (char *)0);
        } else {
            execl("/bin/bash", "bash", "-c", "bash -c '\"$PYTHON\" \"$HELPER\" --caller-pid $$; :'; :", (char *)0);
        }
        _exit(127);
    }
    int status;
    if (child < 0 || waitpid(child, &status, 0) < 0) return 1;
    return WIFEXITED(status) ? WEXITSTATUS(status) : 1;
}
'''


class AgentPidTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.claude = self.root / 'claude'
        self.claude.symlink_to(sys.executable)
        self.driver = self.root / 'driver.py'
        self.driver.write_text(DRIVER)
        self.stub = self.root / 'stub.py'
        self.stub.write_text(STUB)
        self.db = self.root / 'db.json'
        self.db.write_text(json.dumps({'log': [], 'claims': {}, 'issues': {'5': {'state':'OPEN', 'body':'', 'revision':1}}}))
        foreign = subprocess.Popen(['sleep', '60'])
        self.addCleanup(foreign.wait)
        self.addCleanup(foreign.terminate)
        self.env = dict(os.environ, HELPER=str(HELPER), HOOK=str(HOOK), FOREIGN_PID=str(foreign.pid),
                        DIBS_CLI=f'{sys.executable} {self.stub} {self.db}', DIBS_BLOCK_STATE_DIR=str(self.root / 'state'),
                        DIBS_ATLAS_SYNC='off', SESSIONEER_SELF='tester')
        self.env.pop('DIBS_AGENT_PID', None)

    def agent(self, mode):
        p = subprocess.run([str(self.claude), str(self.driver), str(self.root), mode], env=self.env,
                           text=True, capture_output=True, timeout=15, check=True)
        return json.loads(p.stdout)

    def test_nearest_agent_is_selected_and_foreign_override_is_ignored(self):
        for mode in ('helper', 'foreign'):
            with self.subTest(mode=mode):
                result = self.agent(mode)
                self.assertEqual(result['returncode'], 0, result['stderr'])
                self.assertEqual(result['stdout'].strip(), str(result['pid']))

    def test_independent_agents_with_same_session_name_are_distinct(self):
        first, second = self.agent('helper'), self.agent('helper')
        for result in (first, second):
            self.assertEqual(result['returncode'], 0, result['stderr'])
            self.assertEqual(result['stdout'].strip(), str(result['pid']))
        self.assertNotEqual(first['stdout'], second['stdout'])

    def test_fallback_is_the_original_caller_not_the_helper_or_supervisor(self):
        # PID 1 has no parent, so the surrounding test runner can itself run
        # beneath Claude without turning this into an ancestor-selection test.
        init_name = Path('/proc/1/comm').read_text().strip().lower()
        if init_name == 'claude':
            self.skipTest('PID 1 is itself a Claude agent')
        result = subprocess.run([sys.executable, str(HELPER), '--caller-pid', '1'],
                                env=self.env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), '1')

    def native_agent(self, args, service=None):
        source = self.root / 'fake-claude.c'
        source.write_text(FAKE_CLAUDE)
        binary = self.root / 'native' / 'claude'
        binary.parent.mkdir(exist_ok=True)
        subprocess.run(['cc', str(source), '-o', str(binary)], check=True, capture_output=True)
        env = self.env | {'FAKE_CLAUDE': str(binary), 'PYTHON': sys.executable}
        if service:
            env['FAKE_SERVICE'] = service
        else:
            env.pop('FAKE_SERVICE', None)
        run = subprocess.run([str(binary), *args], env=env, capture_output=True, text=True, timeout=15)
        self.assertEqual(run.returncode, 0, run.stderr)
        owners = [int(line.split('=', 1)[1]) for line in run.stderr.splitlines() if line.startswith('agent-pid=')]
        return owners, int(run.stdout.strip())

    def test_prompt_and_option_values_named_for_services_remain_agents(self):
        for args in (['-p', 'daemon'], ['-p', 'supervisor'], ['--model', 'daemon'], ['--model', 'supervisor']):
            with self.subTest(args=args):
                owners, selected = self.native_agent(args)
                self.assertEqual(len(owners), 1)
                self.assertEqual(selected, owners[0])

    def test_actual_service_commands_are_skipped_in_favor_of_agent_ancestor(self):
        for service in ('daemon', 'supervisor'):
            with self.subTest(service=service):
                owners, selected = self.native_agent(['-p', 'ordinary'], service)
                self.assertEqual(len(owners), 2)
                self.assertNotEqual(owners[0], owners[1])
                self.assertEqual(selected, owners[0])

    def test_hook_claim_uses_same_agent_identity(self):
        result = self.agent('hook')
        self.assertEqual(result['returncode'], 0, result['stderr'])
        calls = json.loads(self.db.read_text())['log']
        claim = next(call for call in calls if call[0] == 'claim')
        self.assertIn('--pid=' + str(result['pid']), claim)


if __name__ == '__main__':
    unittest.main()
