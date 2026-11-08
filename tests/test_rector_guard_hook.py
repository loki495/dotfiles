"""ai/hooks/rector-guard.sh denies rector process without --dry-run."""
import json
from pathlib import Path
import subprocess
import unittest

HOOK = Path(__file__).resolve().parents[1] / 'ai' / 'hooks' / 'rector-guard.sh'


def run(cmd):
    out = subprocess.run([str(HOOK)], input=json.dumps({'tool_input': {'command': cmd}}),
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)['hookSpecificOutput']['permissionDecision'] if out else None


class RectorGuardTests(unittest.TestCase):
    def test_denies_apply(self):
        for cmd in ('docker exec app ./vendor/bin/rector process',
                    'vendor/bin/rector process app --no-progress-bar',
                    'composer rector:apply', 'cd x && vendor/bin/rector process'):
            self.assertEqual(run(cmd), 'deny', cmd)

    def test_allows_dry_run_and_unrelated(self):
        for cmd in ('docker exec app ./vendor/bin/rector process --dry-run',
                    'vendor/bin/rector process --dry-run --no-progress-bar',
                    'composer rector', 'git status', 'grep rector README.md'):
            self.assertIsNone(run(cmd), cmd)


if __name__ == '__main__':
    unittest.main()
