"""ai/hooks/flow-offer.sh: a Stop hook that turns the reply's status line into a --next intent, silently.

Intent of this group: the hook is the bridge between the rule-1226 status line and the dashboard offer.
Each status line maps to exactly one intent, the call is `--next --intent <intent> --post` against
$SESSIONEER_BIN (else `sessioneer` on PATH), and every other shape (no status line, no SESSIONEER_SELF,
a failing or hanging binary, junk stdin) prints nothing and exits 0 so the turn is never blocked.
"""
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / 'ai' / 'hooks' / 'flow-offer.sh'

CASES = [
    ('Safe to archive this session.', 'done'),
    ('All planned work is done.', 'done'),
    ('Continue in this session: finish the tests and commit.', 'step-end'),
    ('Continue in a different session: a receiver has room and this one is nearly out of quota.', 'step-end'),
    ('Waiting on Andres: which branch should the PR target?', 'wait'),
    ('Waiting on other work: the runner is still going in the sibling session.', 'wait'),
]


class FlowOfferTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: subprocess.run(['rm', '-rf', str(self.tmp)]))
        self.calls = self.tmp / 'calls'
        self.bin = self.tmp / 'sessioneer'
        self.stub()

    def stub(self, out='', rc=0, sleep=0, path=None):
        path = path or self.bin
        body = ['#!/bin/sh', f'echo "$@" >> {self.calls}']
        if sleep:
            # exec, so the timeout kills this very process and nothing keeps the pipe open
            body.append(f'exec sleep {sleep}')
        else:
            body += [f"printf '%s' {shlex.quote(out)}", f'exit {rc}']
        path.write_text('\n'.join(body) + '\n')
        os.chmod(path, 0o755)
        return path

    def env(self, session='sess-1', bin_path=None, path=None):
        env = {k: v for k, v in os.environ.items() if k not in ('SESSIONEER_SELF', 'SESSIONEER_BIN')}
        if bin_path is False:
            env['PATH'] = path
        else:
            env['SESSIONEER_BIN'] = str(bin_path or self.bin)
        if session is not None:
            env['SESSIONEER_SELF'] = session
        return env

    def run_hook(self, payload, timeout=20, **kw):
        raw = payload if isinstance(payload, str) else json.dumps(payload)
        started = time.monotonic()
        proc = subprocess.run([str(HOOK)], input=raw, capture_output=True, text=True,
                              env=self.env(**kw), timeout=timeout)
        return proc, time.monotonic() - started

    def calls_made(self):
        if not self.calls.exists():
            return []
        return [line.split() for line in self.calls.read_text().splitlines() if line.strip()]

    def assert_silent(self, proc):
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, '')


class FlowOfferMappingTest(FlowOfferTest):
    def test_each_status_line_posts_its_intent_with_the_exact_arguments(self):
        for line, intent in CASES:
            with self.subTest(line=line):
                if self.calls.exists():
                    self.calls.unlink()
                proc, _ = self.run_hook({'last_assistant_message': line})
                self.assert_silent(proc)
                self.assertEqual(self.calls_made(), [['--next', '--intent', intent, '--post']])

    def test_the_status_line_is_trimmed_and_trailing_blank_lines_are_ignored(self):
        message = 'Done with the step.\n\n   Waiting on Andres: pick the branch   \n\n'
        proc, _ = self.run_hook({'last_assistant_message': message})
        self.assert_silent(proc)
        self.assertEqual(self.calls_made(), [['--next', '--intent', 'wait', '--post']])

    def test_an_earlier_status_line_does_not_count_when_more_text_follows(self):
        message = 'Safe to archive this session.\n\nOne last remark.'
        proc, _ = self.run_hook({'last_assistant_message': message})
        self.assert_silent(proc)
        self.assertEqual(self.calls_made(), [])

    def test_message_is_the_fallback_when_last_assistant_message_is_absent(self):
        proc, _ = self.run_hook({'message': 'Waiting on Andres: pick the branch'})
        self.assert_silent(proc)
        self.assertEqual(self.calls_made(), [['--next', '--intent', 'wait', '--post']])

    def test_last_assistant_message_wins_when_both_are_present(self):
        proc, _ = self.run_hook({'last_assistant_message': 'All planned work is done.',
                                 'message': 'Waiting on Andres: pick the branch'})
        self.assert_silent(proc)
        self.assertEqual(self.calls_made(), [['--next', '--intent', 'done', '--post']])

    def test_the_bin_falls_back_to_sessioneer_on_the_path(self):
        bindir = self.tmp / 'bin'
        bindir.mkdir()
        self.stub(path=bindir / 'sessioneer')
        proc, _ = self.run_hook({'last_assistant_message': 'Continue in this session: next step'},
                                bin_path=False, path=f'{bindir}:{os.environ["PATH"]}')
        self.assert_silent(proc)
        self.assertEqual(self.calls_made(), [['--next', '--intent', 'step-end', '--post']])


class FlowOfferSilenceTest(FlowOfferTest):
    def test_a_reply_without_a_status_line_starts_nothing(self):
        for message in ('All good, the tests pass.',
                        'Safe to archive this session',        # the exact prefix has its full stop
                        'Continue in this session - done',     # the exact prefix has its colon
                        'safe to archive this session.',
                        'Waiting on Andres and the runner.'):
            with self.subTest(message=message):
                proc, _ = self.run_hook({'last_assistant_message': message})
                self.assert_silent(proc)
                self.assertEqual(self.calls_made(), [])

    def test_an_empty_or_missing_message_starts_nothing(self):
        for payload in ({'last_assistant_message': ''}, {}, {'last_assistant_message': '   \n\n'}):
            with self.subTest(payload=payload):
                proc, _ = self.run_hook(payload)
                self.assert_silent(proc)
                self.assertEqual(self.calls_made(), [])

    def test_without_sessioneer_self_nothing_runs(self):
        proc, _ = self.run_hook({'last_assistant_message': 'Waiting on Andres: pick the branch'}, session=None)
        self.assert_silent(proc)
        self.assertEqual(self.calls_made(), [])

    def test_a_failing_binary_is_silent_and_still_exits_zero(self):
        self.stub(out='sessioneer: no host agent', rc=1)
        proc, _ = self.run_hook({'last_assistant_message': 'All planned work is done.'})
        self.assert_silent(proc)
        self.assertEqual(len(self.calls_made()), 1)

    def test_a_hanging_binary_never_blocks_the_turn(self):
        self.stub(sleep=10)
        proc, elapsed = self.run_hook({'last_assistant_message': 'Safe to archive this session.'})
        self.assert_silent(proc)
        self.assertLess(elapsed, 8, 'the hook must bound the sessioneer call with a short timeout')

    def test_valid_json_is_always_accepted(self):
        for payload in ({}, {'session_id': 's1'}, {'last_assistant_message': None},
                        {'last_assistant_message': 'no status here', 'message': 'nor here'}):
            with self.subTest(payload=payload):
                proc, _ = self.run_hook(payload)
                self.assert_silent(proc)
                self.assertEqual(self.calls_made(), [])

    def test_unreadable_stdin_still_exits_zero(self):
        proc, _ = self.run_hook('not json at all')
        self.assert_silent(proc)
        self.assertEqual(self.calls_made(), [])


if __name__ == '__main__':
    unittest.main()
