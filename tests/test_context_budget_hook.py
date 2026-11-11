"""ai/hooks/context-budget.sh: thresholds come from the session-flow thresholds file; CLAUDE_CTX_* overrides win."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / 'ai' / 'hooks' / 'context-budget.sh'
THRESHOLDS = ROOT / 'ai' / 'skills' / 'session-flow' / 'thresholds.conf'


def run(tokens, idle_min=0, env=None, prompt='go on'):
    with tempfile.TemporaryDirectory() as tmp:
        ts = (datetime.now(timezone.utc) - timedelta(minutes=idle_min)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
        transcript = Path(tmp) / 't.jsonl'
        transcript.write_text(json.dumps({'type': 'assistant', 'timestamp': ts,
                                          'message': {'usage': {'input_tokens': tokens}}}) + '\n')
        proc = subprocess.run([str(HOOK)], capture_output=True, text=True,
                              input=json.dumps({'prompt': prompt, 'transcript_path': str(transcript), 'session_id': 's'}),
                              env={**os.environ, 'XDG_RUNTIME_DIR': tmp, **(env or {})})
        return json.loads(proc.stdout) if proc.stdout.strip() else None


class ContextBudgetHookTest(unittest.TestCase):
    def test_thresholds_file_defines_every_number(self):
        text = THRESHOLDS.read_text()
        for name in ('CTX_GO_MAX', 'QUOTA_GO_MAX', 'CTX_ROTATE', 'QUOTA_PARK', 'QUOTA_CARRY', 'IDLE_MIN', 'IDLE_FLOOR'):
            self.assertRegex(text, rf'(?m)^{name}=\d+$')

    def test_under_the_rotate_threshold_is_silent(self):
        self.assertIsNone(run(90000))

    def test_over_the_rotate_threshold_from_the_file_warns_and_names_session_flow(self):
        context = run(260000)['hookSpecificOutput']['additionalContext']
        self.assertIn('session-flow', context)
        self.assertIn('AskUserQuestion', context)

    def test_a_threshold_file_override_changes_the_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            conf = Path(tmp) / 't.conf'
            conf.write_text('CTX_ROTATE=50000\n')
            self.assertIn('hookSpecificOutput', run(60000, env={'SESSION_FLOW_THRESHOLDS': str(conf)}))

    def test_environment_override_wins_over_the_file(self):
        self.assertIsNone(run(260000, env={'CLAUDE_CTX_BUDGET': '400000'}))

    def test_idle_with_a_big_context_blocks_once(self):
        out = run(120000, idle_min=90)
        self.assertEqual(out['decision'], 'block')
        self.assertIn('session-flow', out['reason'])

    def test_slash_commands_pass_through(self):
        self.assertIsNone(run(300000, prompt='/handoff'))


if __name__ == '__main__':
    unittest.main()
