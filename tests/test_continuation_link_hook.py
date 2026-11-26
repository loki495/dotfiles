"""ai/hooks/continuation-link.py: links a session to the session it continues.

Claude UserPromptSubmit hook. It reads the prompt, finds the source session, tells Claude that
Sessioneer archives it, and a worker runs `sessioneer --replaces SOURCE --session <session_id> --json`.
Tests set SESSIONEER_BIN (a fake that records its argv and prints scripted replies), DIBS_SHOW_CMD (a
fake Dibs reader), CONTINUATION_LINK_DIR (a temp dir), CONTINUATION_LINK_FOREGROUND=1 (worker inline),
CONTINUATION_LINK_RETRY_SECONDS (sleep between tries) and CONTINUATION_LINK_RETRY_LIMIT (total
seconds); HOME and XDG_RUNTIME_DIR point into the temp dir, so nothing real is touched.

Intent of the groups:
- Gate: never blocks (exit 0) on junk stdin, missing fields, failing tools; no match is silent with no call.
- Takeover / SourceLine / SessionLine: the three prompt patterns, their source extraction and negatives.
- Handoff / PlanComment: Dibs-backed patterns, first prompt only, failing or odd Dibs reads mean no match.
- Precedence: first match wins in the order takeover, Source session, Session line, handoff, plan comment.
- SelfSource and Seen: own id ignored; the .seen marker is created on the first prompt.
- Context: the additionalContext text. Worker: argv, retry only on an unknown receiver, limit, refusal
  message file delivered once on the next prompt. Detached: the hook returns while the worker runs.
- Unsafe: symlinked or foreign directory and symlinked .msg/.seen files are never written or trusted.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / 'ai' / 'hooks' / 'continuation-link.py'

SESSIONEER_STUB = '''#!/usr/bin/env python3
import json, os, sys, time
CFG, CALLS, COUNT = {cfg!r}, {calls!r}, {count!r}
with open(CALLS, 'a') as f:
    f.write(json.dumps(sys.argv[1:]) + '\\n')
spec = json.load(open(CFG)).get('replies') or [{{'out': {{'ok': True}}}}]
n = int(open(COUNT).read()) if os.path.exists(COUNT) else 0
open(COUNT, 'w').write(str(n + 1))
spec = spec[min(n, len(spec) - 1)]
if spec.get('sleep'):
    time.sleep(spec['sleep'])
out = spec.get('out', '')
sys.stdout.write(out if isinstance(out, str) else json.dumps(out))
sys.exit(spec.get('rc', 0))
'''

DIBS_STUB = '''#!/usr/bin/env python3
import json, sys
CFG, CALLS = {cfg!r}, {calls!r}
with open(CALLS, 'a') as f:
    f.write(json.dumps(sys.argv[1:]) + '\\n')
cfg = json.load(open(CFG))
if cfg.get('rc'):
    sys.exit(cfg['rc'])
if 'raw' in cfg:
    sys.stdout.write(cfg['raw'])
    sys.exit(0)
args = [a for a in sys.argv[1:] if a != '--all-comments']
task = cfg.get('tasks', {{}}).get(args[-1])
if task is None:
    sys.exit(1)
sys.stdout.write(json.dumps(task))
'''

REFUSED_UNKNOWN = {'ok': False, 'message': 'Unknown session me-1'}
OK_REPLY = {'ok': True, 'source': 'old', 'receiver': 'new', 'outcome': 'waiting', 'detail': 'still working'}
ARCHIVE_TEXT = 'Sessioneer archives it once it is idle and holds no claim; do not archive it yourself'


def task(n, labels, body, comments=None):
    return {'id': n, 'labels': labels, 'body': body,
            'comments': {'items': comments or [], 'complete': True}}


class HookTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: subprocess.run(['rm', '-rf', str(self.tmp)]))
        self.linkdir = self.tmp / 'link'
        self.calls_file = self.tmp / 'calls'
        self.dibs_calls_file = self.tmp / 'dibs-calls'
        self.cfg = self.tmp / 'cfg.json'
        self.dibs_cfg = self.tmp / 'dibs.json'
        self.bin = self.tmp / 'sessioneer'
        self.bin.write_text(SESSIONEER_STUB.format(cfg=str(self.cfg), calls=str(self.calls_file),
                                                   count=str(self.tmp / 'count')))
        os.chmod(self.bin, 0o755)
        self.dibs = self.tmp / 'dibs-show'
        self.dibs.write_text(DIBS_STUB.format(cfg=str(self.dibs_cfg), calls=str(self.dibs_calls_file)))
        os.chmod(self.dibs, 0o755)
        self.plain = self.tmp / 'plain'
        self.plain.mkdir()
        self.outside = self.tmp / 'outside.txt'
        self.outside.write_text('original')
        self.replies([{'out': OK_REPLY}])
        self.dibs_config({})

    def replies(self, specs):
        self.cfg.write_text(json.dumps({'replies': specs}))

    def dibs_config(self, tasks, **extra):
        self.dibs_cfg.write_text(json.dumps({'tasks': {str(k): v for k, v in tasks.items()}, **extra}))

    def env(self, foreground=True, dibs_cmd=None, retry='0.01', limit='5', bin_path=None, edit=None):
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(('CONTINUATION_LINK', 'SESSIONEER', 'DIBS_'))}
        env.update({'CONTINUATION_LINK_DIR': str(self.linkdir), 'SESSIONEER_BIN': str(bin_path or self.bin),
                    'DIBS_SHOW_CMD': dibs_cmd or str(self.dibs), 'CONTINUATION_LINK_RETRY_SECONDS': retry,
                    'CONTINUATION_LINK_RETRY_LIMIT': limit, 'HOME': str(self.tmp),
                    'XDG_RUNTIME_DIR': str(self.tmp / 'xdg')})
        if foreground:
            env['CONTINUATION_LINK_FOREGROUND'] = '1'
        if edit:
            edit(env)
        return env

    def run_hook(self, prompt='hello', session_id='me-1', raw=None, timeout=25, **kw):
        self.assertTrue(HOOK.exists(), f'hook missing: {HOOK}')
        if raw is None:
            payload = {'hook_event_name': 'UserPromptSubmit', 'session_id': session_id,
                       'prompt': prompt, 'cwd': str(self.plain), 'transcript_path': '/nonexistent'}
            raw = json.dumps({k: v for k, v in payload.items() if v is not None})
        return subprocess.run([sys.executable, str(HOOK)], input=raw, capture_output=True, text=True,
                              env=self.env(**kw), timeout=timeout, cwd=str(self.plain))

    def read_calls(self, path):
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

    def calls(self):
        return self.read_calls(self.calls_file)

    def dibs_calls(self):
        return self.read_calls(self.dibs_calls_file)

    def context(self, proc):
        self.assertEqual(proc.returncode, 0, proc.stderr)
        if not proc.stdout.strip():
            return None
        out = json.loads(proc.stdout)
        return out['hookSpecificOutput']['additionalContext']

    def replaces_argv(self, source, session_id='me-1'):
        return ['--replaces', source, '--session', session_id, '--json']

    def assert_linked(self, prompt, source, session_id='me-1', **kw):
        proc = self.run_hook(prompt, session_id=session_id, **kw)
        ctx = self.context(proc)
        self.assertIsNotNone(ctx, f'no context for {prompt!r}')
        self.assertIn(source, ctx)
        self.assertEqual(self.calls(), [self.replaces_argv(source, session_id)])
        return proc

    def assert_silent(self, prompt, **kw):
        proc = self.run_hook(prompt, **kw)
        self.assertEqual((proc.returncode, proc.stdout), (0, ''), proc.stderr)
        self.assertEqual(self.calls(), [])
        return proc

    def mark_seen(self, session_id='me-1'):
        self.linkdir.mkdir(mode=0o700, exist_ok=True)
        (self.linkdir / f'{session_id}.seen').write_text('')

    def msg_path(self, sid='me-1'):
        return self.linkdir / f'{sid}.msg'


class GateTest(HookTest):
    def test_junk_stdin_is_silent_and_exits_zero(self):
        for raw in ['', 'not json', '[]', 'null', '"x"', '{', '{"session_id": 5, "prompt": 7}']:
            with self.subTest(raw=raw):
                proc = self.run_hook(raw=raw)
                self.assertEqual((proc.returncode, proc.stdout), (0, ''), proc.stderr)
        self.assertEqual(self.calls(), [])

    def test_missing_or_non_string_fields_are_silent(self):
        for payload in [{'prompt': '/takeover claude abc'}, {'session_id': 'me-1'},
                        {'session_id': 'me-1', 'prompt': ['/takeover claude abc']},
                        {'session_id': '', 'prompt': '/takeover claude abc'}]:
            with self.subTest(payload=payload):
                proc = self.run_hook(raw=json.dumps(payload))
                self.assertEqual((proc.returncode, proc.stdout), (0, ''), proc.stderr)
        self.assertEqual(self.calls(), [])

    def test_unknown_payload_keys_are_ignored(self):
        raw = json.dumps({'session_id': 'me-1', 'prompt': '/takeover claude abc-1', 'extra': {'a': 1}})
        proc = self.run_hook(raw=raw)
        self.assertIn('abc-1', self.context(proc))
        self.assertEqual(self.calls(), [self.replaces_argv('abc-1')])

    def test_a_plain_prompt_has_no_output_and_no_call(self):
        self.assert_silent('Please fix the failing test in the billing module.')
        self.assertEqual(self.dibs_calls(), [])

    def test_a_missing_sessioneer_binary_still_exits_zero(self):
        proc = self.run_hook('/takeover claude abc-1', bin_path=self.tmp / 'nope')
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_a_crashing_sessioneer_exits_zero_without_a_retry(self):
        self.replies([{'rc': 3, 'out': 'garbage'}])
        proc = self.run_hook('/takeover claude abc-1')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(len(self.calls()), 1)

    def test_a_non_json_sessioneer_reply_exits_zero_without_a_retry(self):
        self.replies([{'out': 'replaces abc-1: waiting'}])
        proc = self.run_hook('/takeover claude abc-1')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(len(self.calls()), 1)


class TakeoverTest(HookTest):
    def test_takeover_with_agent_and_id(self):
        self.assert_linked('/takeover claude conv-aaa-111', 'conv-aaa-111')

    def test_takeover_with_agent_profile_and_id(self):
        self.assert_linked('/takeover claude work conv-bbb-222', 'conv-bbb-222')

    def test_takeover_other_agents(self):
        for agent in ['codex', 'opencode']:
            with self.subTest(agent=agent):
                self.calls_file.unlink(missing_ok=True)
                (self.tmp / 'count').unlink(missing_ok=True)
                self.linkdir_clear()
                self.assert_linked(f'/takeover {agent} id-{agent}-9', f'id-{agent}-9')

    def linkdir_clear(self):
        subprocess.run(['rm', '-rf', str(self.linkdir)])

    def test_takeover_with_a_trailing_newline_or_text_on_later_lines(self):
        self.assert_linked('/takeover claude conv-ccc-333\n', 'conv-ccc-333')

    def test_skill_form_without_profile(self):
        prompt = 'Read the takeover skill for source codex 019a-uuid-77 and follow it.'
        proc = self.run_hook(prompt)
        self.assertIn('019a-uuid-77', self.context(proc))
        self.assertEqual(self.calls(), [self.replaces_argv('019a-uuid-77')])

    def test_skill_form_with_profile(self):
        proc = self.run_hook('Use the takeover skill for source claude work conv-ddd-444\nThen report.')
        self.assertIn('conv-ddd-444', self.context(proc))
        self.assertEqual(self.calls(), [self.replaces_argv('conv-ddd-444')])

    def test_takeover_must_start_the_prompt(self):
        self.assert_silent('Please do not run /takeover claude conv-eee-555 yet.')

    def test_takeover_without_an_id_is_no_match(self):
        self.assert_silent('/takeover')
        self.assert_silent('/takeover claude')

    def test_takeover_applies_only_when_it_starts_the_prompt_even_after_blank_prompt_text(self):
        self.assert_silent('takeover claude conv-fff-666')


class SourceLineTest(HookTest):
    def test_name_and_id_prefers_the_id(self):
        prompt = ('Continue the migration.\n\nSource session: cc-old-1 conv-ggg-777 (claude). Claim your Dibs '
                  'task first. Sessioneer archives the source as soon as it is idle.')
        proc = self.run_hook(prompt)
        self.assertIn('conv-ggg-777', self.context(proc))
        self.assertEqual(self.calls(), [self.replaces_argv('conv-ggg-777')])

    def test_name_only_uses_the_name(self):
        proc = self.run_hook('Go on.\n\nSource session: cc-old-2 (codex). Claim your Dibs task first.')
        self.assertIn('cc-old-2', self.context(proc))
        self.assertEqual(self.calls(), [self.replaces_argv('cc-old-2')])

    def test_the_line_may_be_the_whole_prompt_without_a_trailing_sentence(self):
        self.assert_linked('Source session: cc-old-3 conv-hhh-888 (opencode).', 'conv-hhh-888')

    def test_only_a_line_starting_with_the_label_counts(self):
        self.assert_silent('He wrote "Source session: cc-old-4 (claude)." in the old doc.')

    def test_a_label_without_a_source_is_no_match(self):
        self.assert_silent('Source session: (claude).')
        self.assert_silent('Source session:')


class SessionLineTest(HookTest):
    def test_agent_and_id(self):
        self.assert_linked('Resume the work.\nSession: claude conv-iii-999\nThanks.', 'conv-iii-999')

    def test_handoff_form_with_dots(self):
        self.assert_linked('Session: codex · 019b-uuid-12 · /home/x/www/proj · fix/thing', '019b-uuid-12')

    def test_the_id_is_never_the_agent_or_workdir(self):
        proc = self.run_hook('Session: claude · conv-jjj-000 · /w/proj · main')
        self.assertEqual(self.calls(), [self.replaces_argv('conv-jjj-000')])
        self.assertIsNotNone(self.context(proc))

    def test_agent_alone_is_no_match(self):
        self.assert_silent('Session: claude')

    def test_a_line_that_does_not_start_with_the_label_is_no_match(self):
        self.assert_silent('Note the Session: claude conv-kkk-111 in the header.')


class HandoffTest(HookTest):
    BODY = 'Handoff for the receiver.\n\nSession: claude · conv-hand-1 · /w/p · main\nNext: finish.'

    def setUp(self):
        super().setUp()
        self.dibs_config({12: task(12, ['handoff', 'temporary'], self.BODY)})

    def test_handoff_in_dibs_task(self):
        proc = self.run_hook('Take over from the handoff in Dibs task 12.')
        self.assertIn('conv-hand-1', self.context(proc))
        self.assertEqual(self.calls(), [self.replaces_argv('conv-hand-1')])
        self.assertEqual(self.dibs_calls(), [['12']])

    def test_short_handoff_form(self):
        self.assert_linked('Please continue from handoff 12 now.', 'conv-hand-1')

    def test_dibs_cmd_is_split_into_arguments(self):
        self.assert_linked('handoff 12', 'conv-hand-1', dibs_cmd=f'{self.dibs} --flag')
        self.assertEqual(self.dibs_calls(), [['--flag', '12']])

    def test_a_task_without_the_handoff_label_is_no_match(self):
        self.dibs_config({12: task(12, ['bug'], self.BODY)})
        self.assert_silent('handoff 12')

    def test_a_body_without_a_session_line_is_no_match(self):
        self.dibs_config({12: task(12, ['handoff'], 'No source recorded here.')})
        self.assert_silent('handoff 12')

    def test_an_unknown_task_is_no_match(self):
        self.assert_silent('handoff 404')
        self.assertEqual(self.dibs_calls(), [['404']])

    def test_not_the_first_prompt_makes_no_dibs_call(self):
        self.mark_seen()
        self.assert_silent('handoff 12')
        self.assertEqual(self.dibs_calls(), [])

    def test_the_first_prompt_creates_the_seen_marker(self):
        self.run_hook('handoff 12')
        self.assertTrue((self.linkdir / 'me-1.seen').exists())

    def test_the_marker_is_created_even_without_a_match(self):
        self.run_hook('just a question')
        self.assertTrue((self.linkdir / 'me-1.seen').exists())
        self.assert_silent('handoff 12')

    def test_another_session_has_its_own_marker(self):
        self.mark_seen('other-7')
        self.assert_linked('handoff 12', 'conv-hand-1')

    def test_dibs_failures_are_no_match(self):
        cases = {'nonzero exit': {'rc': 1}, 'not json': {'raw': 'task not found'},
                 'json array': {'raw': '[]'}, 'empty': {'raw': ''},
                 'wrong shape': {'raw': json.dumps({'id': 12})}}
        for label, extra in cases.items():
            with self.subTest(label):
                self.linkdir_clear()
                self.dibs_config({12: task(12, ['handoff'], self.BODY)}, **extra)
                self.assert_silent('handoff 12')

    def test_a_missing_dibs_command_is_no_match(self):
        self.assert_silent('handoff 12', dibs_cmd=str(self.tmp / 'no-such-dibs'))

    def linkdir_clear(self):
        subprocess.run(['rm', '-rf', str(self.linkdir)])


class PlanCommentTest(HookTest):
    COMMENTS = [{'id': 90, 'body': 'Earlier note\nSession: claude conv-old-0'},
                {'id': 99, 'body': 'Checkpoint of step 3.\nSession: codex conv-plan-1\nNext: step 4.'},
                {'id': 101, 'body': 'Checkpoint without a session.'}]

    def setUp(self):
        super().setUp()
        self.dibs_config({7: task(7, ['plan'], 'Plan body\nSession: claude conv-from-body', self.COMMENTS)})

    def test_resume_plan_from_comment(self):
        proc = self.run_hook('Resume plan 7 from comment 99.')
        self.assertIn('conv-plan-1', self.context(proc))
        self.assertEqual(self.calls(), [self.replaces_argv('conv-plan-1')])
        self.assertEqual(self.dibs_calls(), [['7', '--all-comments']])

    def test_the_named_comment_is_used_not_the_first(self):
        self.assert_linked('Continue plan 7, comment 90 has the checkpoint.', 'conv-old-0')

    def test_a_comment_without_a_session_line_is_no_match(self):
        self.assert_silent('resume plan 7 from comment 101')

    def test_a_missing_comment_is_no_match(self):
        self.assert_silent('resume plan 7 from comment 555')

    def test_a_plan_without_a_comment_number_is_no_match(self):
        self.assert_silent('resume plan 7')
        self.assertEqual(self.dibs_calls(), [])

    def test_not_the_first_prompt_makes_no_dibs_call(self):
        self.mark_seen()
        self.assert_silent('resume plan 7 from comment 99')
        self.assertEqual(self.dibs_calls(), [])

    def test_dibs_failures_are_no_match(self):
        for label, extra in {'nonzero exit': {'rc': 2}, 'not json': {'raw': 'oops'},
                             'comments missing': {'raw': json.dumps({'id': 7, 'labels': [], 'body': ''})}}.items():
            with self.subTest(label):
                subprocess.run(['rm', '-rf', str(self.linkdir)])
                self.dibs_config({7: task(7, ['plan'], '', self.COMMENTS)}, **extra)
                self.assert_silent('resume plan 7 from comment 99')


class PrecedenceTest(HookTest):
    def setUp(self):
        super().setUp()
        self.dibs_config({12: task(12, ['handoff'], 'Session: claude · conv-hand-1 · /w · main'),
                          7: task(7, ['plan'], '', [{'id': 99, 'body': 'Session: claude conv-plan-1'}])})

    def test_takeover_beats_source_session_and_session_line(self):
        prompt = ('/takeover claude conv-take-1\nSource session: cc-x conv-src-1 (claude).\n'
                  'Session: claude conv-line-1')
        self.assert_linked(prompt, 'conv-take-1')

    def test_source_session_beats_session_line(self):
        self.assert_linked('Session: claude conv-line-1\nSource session: cc-x conv-src-1 (claude).', 'conv-src-1')

    def test_session_line_beats_handoff_and_plan(self):
        self.assert_linked('Session: claude conv-line-1\nhandoff 12 and resume plan 7 from comment 99', 'conv-line-1')

    def test_handoff_beats_plan_comment(self):
        self.assert_linked('Use handoff 12, or resume plan 7 from comment 99.', 'conv-hand-1')

    def test_a_failing_handoff_falls_through_to_the_plan_comment(self):
        self.dibs_config({7: task(7, ['plan'], '', [{'id': 99, 'body': 'Session: claude conv-plan-1'}])})
        self.assert_linked('handoff 12 or resume plan 7 from comment 99', 'conv-plan-1')


class SelfSourceTest(HookTest):
    def test_takeover_of_the_own_session_is_ignored(self):
        self.assert_silent('/takeover claude me-1')

    def test_source_line_with_the_own_id_is_ignored(self):
        self.assert_silent('Source session: cc-self me-1 (claude).')

    def test_session_line_with_the_own_id_is_ignored(self):
        self.assert_silent('Session: claude me-1')

    def test_handoff_naming_the_own_session_is_ignored(self):
        self.dibs_config({12: task(12, ['handoff'], 'Session: claude · me-1 · /w · main')})
        self.assert_silent('handoff 12')

    def test_another_id_is_still_linked(self):
        self.assert_linked('/takeover claude me-2', 'me-2')


class ContextTest(HookTest):
    def test_output_is_claude_hook_json(self):
        proc = self.run_hook('/takeover claude conv-ctx-1')
        out = json.loads(proc.stdout)
        self.assertEqual(list(out), ['hookSpecificOutput'])
        self.assertEqual(out['hookSpecificOutput'].get('hookEventName'), 'UserPromptSubmit')
        ctx = out['hookSpecificOutput']['additionalContext']
        self.assertIn('conv-ctx-1', ctx)
        self.assertIn(ARCHIVE_TEXT, ctx)

    def test_a_name_source_is_named_in_the_context(self):
        ctx = self.context(self.run_hook('Source session: cc-nm (claude).'))
        self.assertIn('cc-nm', ctx)
        self.assertIn(ARCHIVE_TEXT, ctx)

    def test_a_plain_prompt_without_a_pending_message_has_no_output(self):
        self.assert_silent('hello there')


class WorkerTest(HookTest):
    def test_one_exact_call_and_no_message_on_success(self):
        self.run_hook('/takeover claude conv-w-1', session_id='me-1')
        self.assertEqual(self.calls(), [['--replaces', 'conv-w-1', '--session', 'me-1', '--json']])
        self.assertFalse(self.msg_path().exists())

    def test_the_receiver_is_the_hook_session_id(self):
        self.assert_linked('/takeover claude conv-w-2', 'conv-w-2', session_id='sess-xyz')

    def test_retries_while_the_receiver_is_unknown_then_succeeds(self):
        self.replies([{'out': REFUSED_UNKNOWN}, {'out': REFUSED_UNKNOWN}, {'out': OK_REPLY}])
        proc = self.run_hook('/takeover claude conv-w-3')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.calls(), [self.replaces_argv('conv-w-3')] * 3)
        self.assertFalse(self.msg_path().exists())

    def test_the_retry_limit_stops_the_retrying(self):
        self.replies([{'out': REFUSED_UNKNOWN}])
        started = time.monotonic()
        proc = self.run_hook('/takeover claude conv-w-4', retry='0.05', limit='0.4')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertLess(time.monotonic() - started, 15)
        count = len(self.calls())
        self.assertGreaterEqual(count, 2)
        self.assertLessEqual(count, 20)
        time.sleep(0.3)
        self.assertEqual(len(self.calls()), count)

    def test_another_refusal_is_not_retried_and_goes_to_the_msg_file(self):
        self.replies([{'out': {'ok': False, 'message': 'conv-w-5 is the session that launched you'}},
                      {'out': OK_REPLY}])
        proc = self.run_hook('/takeover claude conv-w-5')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(len(self.calls()), 1)
        self.assertIn('launched you', self.msg_path().read_text())

    def test_the_message_is_shown_on_the_next_prompt_and_deleted(self):
        self.replies([{'out': {'ok': False, 'message': 'already has an open rotation to cc-z'}}])
        self.run_hook('/takeover claude conv-w-6')
        proc = self.run_hook('next question')
        self.assertIn('already has an open rotation to cc-z', self.context(proc))
        self.assertFalse(self.msg_path().exists())
        proc = self.run_hook('another question')
        self.assertEqual((proc.returncode, proc.stdout), (0, ''))
        self.assertEqual(len(self.calls()), 1)

    def test_the_message_of_one_session_is_not_shown_to_another(self):
        self.replies([{'out': {'ok': False, 'message': 'private refusal'}}])
        self.run_hook('/takeover claude conv-w-7', session_id='me-1')
        proc = self.run_hook('hi', session_id='me-2')
        self.assertEqual((proc.returncode, proc.stdout), (0, ''))
        self.assertTrue(self.msg_path('me-1').exists())

    def test_gone_outcome_writes_nothing(self):
        self.replies([{'out': {'ok': True, 'source': 'conv-w-8', 'receiver': 'me-1', 'outcome': 'gone',
                               'detail': 'the source is not a tracked session'}}])
        self.run_hook('/takeover claude conv-w-8')
        self.assertEqual(list(self.linkdir.glob('*.msg')), [])

    def test_a_session_id_with_path_characters_stays_inside_the_directory(self):
        self.replies([{'out': {'ok': False, 'message': 'refused'}}])
        proc = self.run_hook('/takeover claude conv-w-9', session_id='../evil/x')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual([p.name for p in self.tmp.iterdir() if 'evil' in p.name], [])
        for p in self.tmp.rglob('*'):
            if p.suffix in ('.msg', '.seen'):
                self.assertEqual(p.parent, self.linkdir)


class DetachedTest(HookTest):
    def test_the_hook_returns_while_a_slow_worker_runs(self):
        self.replies([{'sleep': 3, 'out': OK_REPLY}])
        started = time.monotonic()
        proc = self.run_hook('/takeover claude conv-d-1', foreground=False)
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 2.5)
        self.assertIn('conv-d-1', self.context(proc))
        deadline = time.monotonic() + 8
        while not self.calls() and time.monotonic() < deadline:
            time.sleep(0.1)
        self.assertEqual(self.calls(), [self.replaces_argv('conv-d-1')])
        time.sleep(3.2)

    def test_the_detached_worker_writes_a_refusal_message(self):
        self.replies([{'out': {'ok': False, 'message': 'detached refusal'}}])
        self.run_hook('/takeover claude conv-d-2', foreground=False)
        deadline = time.monotonic() + 8
        while not self.msg_path().exists() and time.monotonic() < deadline:
            time.sleep(0.1)
        self.assertIn('detached refusal', self.msg_path().read_text())


class UnsafeTest(HookTest):
    REFUSAL = [{'out': {'ok': False, 'message': 'refusal text'}}]

    def linked_dir(self):
        real = self.tmp / 'real'
        real.mkdir()
        self.linkdir = self.tmp / 'linkdir'
        self.linkdir.symlink_to(real)
        return real

    def test_a_symlinked_dir_is_never_written(self):
        real = self.linked_dir()
        self.replies(self.REFUSAL)
        proc = self.run_hook('/takeover claude conv-u-1')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(list(real.iterdir()), [])

    def test_a_symlinked_dir_delivers_nothing(self):
        real = self.linked_dir()
        (real / 'me-1.msg').write_text('injected text')
        proc = self.run_hook('hello')
        self.assertEqual((proc.returncode, proc.stdout), (0, ''))
        self.assertTrue((real / 'me-1.msg').exists())

    def test_a_dir_that_is_a_regular_file_is_harmless(self):
        self.linkdir.write_text('i am a file')
        proc = self.run_hook('hello')
        self.assertEqual((proc.returncode, proc.stdout), (0, ''))
        proc = self.run_hook('/takeover claude conv-u-2')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.linkdir.read_text(), 'i am a file')

    def test_a_created_dir_is_private(self):
        self.run_hook('hello')
        self.assertEqual(os.lstat(self.linkdir).st_mode & 0o777, 0o700)

    def test_a_loose_dir_we_own_is_tightened(self):
        self.linkdir.mkdir()
        os.chmod(self.linkdir, 0o777)
        self.run_hook('hello')
        self.assertEqual(os.lstat(self.linkdir).st_mode & 0o777, 0o700)

    def test_the_worker_never_writes_through_a_symlinked_msg_file(self):
        self.linkdir.mkdir(mode=0o700)
        self.msg_path().symlink_to(self.outside)
        self.replies(self.REFUSAL)
        proc = self.run_hook('/takeover claude conv-u-3')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.outside.read_text(), 'original')

    def test_a_symlinked_msg_file_is_not_delivered(self):
        self.linkdir.mkdir(mode=0o700)
        self.outside.write_text('injected text')
        self.msg_path().symlink_to(self.outside)
        proc = self.run_hook('hello')
        self.assertEqual((proc.returncode, proc.stdout), (0, ''))
        self.assertEqual(self.outside.read_text(), 'injected text')

    def test_a_symlinked_seen_file_is_never_written_through(self):
        self.linkdir.mkdir(mode=0o700)
        (self.linkdir / 'me-1.seen').symlink_to(self.outside)
        proc = self.run_hook('hello')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.outside.read_text(), 'original')

    def test_an_unsafe_dir_does_not_stop_a_takeover_from_exiting_zero(self):
        self.linked_dir()
        proc = self.run_hook('/takeover claude conv-u-4')
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == '__main__':
    unittest.main()
