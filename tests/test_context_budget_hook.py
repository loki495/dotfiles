"""ai/hooks/context-budget.sh: `sessioneer --next` decides when it can, the thresholds file is the fallback."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / 'ai' / 'hooks' / 'context-budget.sh'
THRESHOLDS = ROOT / 'ai' / 'skills' / 'session-flow' / 'thresholds.conf'


def run_proc(tokens, idle_min=0, env=None, prompt='go on'):
    with tempfile.TemporaryDirectory() as tmp:
        ts = (datetime.now(timezone.utc) - timedelta(minutes=idle_min)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
        transcript = Path(tmp) / 't.jsonl'
        transcript.write_text(json.dumps({'type': 'assistant', 'timestamp': ts,
                                          'message': {'usage': {'input_tokens': tokens}}}) + '\n')
        base = {k: v for k, v in os.environ.items() if k not in ('SESSIONEER_SELF', 'SESSIONEER_BIN')}
        base.update({'XDG_RUNTIME_DIR': tmp, 'SESSIONEER_BIN': '/nonexistent/sessioneer'})
        return subprocess.run([str(HOOK)], capture_output=True, text=True,
                              input=json.dumps({'prompt': prompt, 'transcript_path': str(transcript), 'session_id': 's'}),
                              env={**base, **(env or {})})


def run(tokens, idle_min=0, env=None, prompt='go on'):
    proc = run_proc(tokens, idle_min, env, prompt)
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
        self.assertIsNone(run(300000, prompt='/rotate'))


class NextDecisionTest(unittest.TestCase):
    """Intent: the CLI's own decision wins; the thresholds arithmetic still covers a broken binary."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.args = self.tmp / 'args'
        self.bin = self.tmp / 'sessioneer'
        self.conf = self.tmp / 'thresholds.conf'

    def stub(self, out='', rc=0, sleep=0):
        body = ['#!/bin/sh', f'echo "$@" >> {self.args}']
        if sleep:
            # exec, so the timeout kills this very process and nothing keeps the pipe open
            body.append(f'exec sleep {sleep}')
        else:
            body += [f"printf '%s' {shlex.quote(out)}", f'exit {rc}']
        self.bin.write_text('\n'.join(body) + '\n')
        os.chmod(self.bin, 0o755)

    def env(self, **conf):
        self.conf.write_text(''.join(f'{k}={v}\n' for k, v in conf.items()))
        return {'SESSIONEER_BIN': str(self.bin), 'SESSION_FLOW_THRESHOLDS': str(self.conf)}

    def recorded(self):
        return self.args.read_text().split() if self.args.exists() else []

    def test_the_next_state_warns_even_when_the_file_would_stay_silent(self):
        self.stub(json.dumps({'ok': True, 'state': 'ROTATE', 'why': 'context at 260000 tokens',
                              'trigger': 'context'}))
        out = run(90000, env=self.env(CTX_ROTATE=500000))
        self.assertIsNotNone(out, 'a ROTATE decision must produce the over-budget advisory')
        self.assertIn('session-flow', out['hookSpecificOutput']['additionalContext'])

    def test_the_next_call_is_asked_for_the_decision(self):
        self.stub(json.dumps({'ok': True, 'state': 'ROTATE', 'why': 'context at 260000 tokens',
                              'trigger': 'context'}))
        run(90000, env=self.env(CTX_ROTATE=500000))
        self.assertIn('--next', self.recorded())

    def test_a_go_state_stays_silent_even_when_the_file_would_warn(self):
        self.stub(json.dumps({'ok': True, 'state': 'GO', 'why': 'context 90000, quota 12%',
                              'trigger': 'none'}))
        self.assertIsNone(run(90000, env=self.env(CTX_ROTATE=50000)))

    def test_a_hanging_binary_does_not_hold_the_prompt(self):
        self.stub(sleep=10)
        started = time.monotonic()
        proc = run_proc(90000, env=self.env(CTX_ROTATE=500000))
        elapsed = time.monotonic() - started
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('--next', self.recorded())
        self.assertLess(elapsed, 4, 'the --next call must carry a short timeout')


if __name__ == '__main__':
    unittest.main()
