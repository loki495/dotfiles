"""ai/hooks/stop-gate.sh: status line first, then the dibs block / [complete] lines, then a status-dependent claim check."""
import json
import os
from claude_agent_fixture import use_test_process_as_claude
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dibs_block_hook import STUB as DIBS_STUB  # noqa: E402

HOOK = Path(__file__).resolve().parents[1] / 'ai' / 'hooks' / 'stop-gate.sh'
BLOCK = Path(__file__).resolve().parents[1] / 'ai' / 'hooks' / 'dibs-block.py'
SAFE = 'Safe to archive this session.'
DONE = 'All planned work is done.'
SAME = 'Continue in this session: finishing the tests.'
OTHER = 'Continue in a different session: the infra half.'
ANDRES = 'Waiting on Andres: a decision.'
WORK = 'Waiting on other work: job 8.'


class StopGateTest(unittest.TestCase):
    def setUp(self):
        use_test_process_as_claude(self)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        t = Path(self.tmp.name)
        (t / 'dibs-stub.py').write_text(DIBS_STUB)
        self.db = t / 'db.json'
        self.db.write_text(json.dumps({'log': [], 'claims': {}, 'issues': {
            '5': {'state': 'OPEN', 'body': 'Goal.', 'revision': 1}, '6': {'state': 'CLOSED', 'body': '', 'revision': 1}}}))
        self.repo = t / 'repo'
        self.repo.mkdir()
        git = ['git', '-C', str(self.repo), '-c', 'user.name=t', '-c', 'user.email=t@t']
        subprocess.run(git + ['init', '-q'], check=True)
        subprocess.run(git + ['commit', '-q', '--allow-empty', '-m', 'one'], check=True)
        self.sha = subprocess.run(git + ['rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
        # never the real Dibs: the dibs-block stop step run by the gate talks to this stub
        self.safe_env = {'DIBS_CLI': f'{sys.executable} {t / "dibs-stub.py"} {self.db}', 'DIBS_BLOCK_STATE_DIR': str(t / 'bstate'),
                         'DIBS_ATLAS_HINTS': str(t / 'hints.jsonl'), 'DIBS_ATLAS_SYNC': 'off', 'DIBS_AGENT_PID': str(os.getpid()),
                         'SESSIONEER_SELF': 'tester', 'SESSIONEER_SPAWNED_CMD': 'echo {"ok":false}'}

    def dbs(self):
        return json.loads(self.db.read_text())

    def calls(self, cmd):
        return [c for c in self.dbs()['log'] if c[0] == cmd]

    def run_hook(self, stub_body, session='sess-1', env=None, extra=None):
        stub = Path(self.tmp.name) / 'claims'
        stub.write_text('#!/usr/bin/env bash\n' + stub_body + '\n')
        stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
        return subprocess.run([str(HOOK)], input=json.dumps({'session_id': session, 'hook_event_name': 'Stop',
                                                              'cwd': str(self.repo), **(extra or {})}),
                              capture_output=True, text=True,
                              env={**os.environ, **self.safe_env, 'DIBS_CLAIMS_CMD': str(stub),
                                   'STOP_GATE_STATE_DIR': str(Path(self.tmp.name) / 'state'), **(env or {})})

    def claim_five_via_block(self):
        p = subprocess.run([sys.executable, str(BLOCK), 'stop'], text=True, capture_output=True, env={**os.environ, **self.safe_env},
                           input=json.dumps({'session_id': 'sess-1', 'cwd': str(self.repo),
                                             'last_assistant_message': '```dibs\nclaim 5\n```'}))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('5', self.dbs()['claims'])

    def dibs_claims_stub(self):
        """A claims answer read from the same fake Dibs the block step writes to."""
        return f'{sys.executable} {Path(self.tmp.name) / "dibs-stub.py"} {self.db} todo:agent:claims "$@"'

    def test_blocks_a_final_message_without_the_status_line_once_per_turn(self):
        out = json.loads(self.run_hook('echo "[]"', extra={'last_assistant_message': 'Done.'}).stdout)
        self.assertEqual(out['decision'], 'block')
        self.assertIn('Rule 1226', out['reason'])
        self.assertIn('output only the missing status line', out['reason'])
        self.assertIn('ask it with AskUserQuestion first', out['reason'])
        self.assertIn('handed this session', out['reason'])
        again = self.run_hook('echo "[]"', extra={'last_assistant_message': 'Done.', 'stop_hook_active': True})
        self.assertEqual(again.stdout.strip(), '')

    def test_allows_each_status_line(self):
        for line in ('Safe to archive this session.', 'Continue in this session: x.',
                     'Continue in a different session: y.', 'Waiting on Andres: a decision.', 'Waiting on other work: job 8.', 'All planned work is done.'):
            proc = self.run_hook('echo "[]"', extra={'last_assistant_message': 'Report.\n' + line})
            self.assertEqual(proc.stdout.strip(), '', line)

    def status_run(self, msg, **extra):
        return self.run_hook('echo "[]"', extra={'last_assistant_message': msg, **extra})

    def test_phrase_in_last_three_nonempty_lines_passes_ignoring_trailing_blanks(self):
        ph = 'Waiting on Andres: a decision.'
        for msg in (ph, f'a\nb\n{ph}\n\n\n', f'a\n{ph}\nx\n\ny\n', f'a\n{ph}\nx\ny'):
            self.assertEqual(self.status_run(msg).stdout.strip(), '', repr(msg))

    def test_phrase_earlier_than_the_last_three_nonempty_lines_blocks_with_1226(self):
        ph = 'All planned work is done.'
        for msg in (f'{ph}\nb\nc\nd', f'{ph}\n\nb\n\nc\nd\n\n', f'I said "{ph}" earlier.\nb\nc\nd'):
            out = json.loads(self.status_run(msg).stdout)
            self.assertEqual(out['decision'], 'block', repr(msg))
            self.assertIn('1226', out['reason'])

    def test_misplaced_phrase_is_not_blocked_when_stop_hook_active(self):
        proc = self.status_run('All planned work is done.\nb\nc\nd', stop_hook_active=True)
        self.assertEqual(proc.stdout.strip(), '')

    def test_absent_message_is_not_blocked(self):
        self.assertEqual(self.run_hook('echo "[]"').stdout.strip(), '')

    HELD = 'echo \'[{"issueId":7,"agentName":"claude:a:sess-1","paths":[]}]\''

    def test_allows_when_no_claim_is_held(self):
        proc = self.run_hook('echo "[]"')
        self.assertEqual((proc.returncode, proc.stdout.strip()), (0, ''))

    # --- strict order: status line, then dibs block / [complete], then the claim check ---

    def test_missing_status_asks_only_for_it_and_runs_nothing_else(self):
        msg = f'Done.\n\n```dibs\nclaim 5\n```\n{'[complete 5 | sha=abc1234 | notes]'}'
        out = json.loads(self.run_hook(self.HELD, extra={'last_assistant_message': msg}).stdout)
        self.assertEqual(out['decision'], 'block')
        self.assertIn('Rule 1226', out['reason'])
        self.assertIn('[complete', out['reason'])
        self.assertIn('dibs', out['reason'])
        self.assertEqual(self.dbs()['log'], [])
        self.assertEqual(self.dbs()['claims'], {})

    def test_missing_status_blocks_before_the_claim_check_even_with_a_claim_held(self):
        out = json.loads(self.run_hook(self.HELD, extra={'last_assistant_message': 'Done.'}).stdout)
        self.assertIn('Rule 1226', out['reason'])
        self.assertNotIn('task 7', out['reason'])

    def test_with_status_present_the_dibs_block_is_applied_first(self):
        msg = f'Done.\n```dibs\nclaim 5\nnote 5: x\n```\n{SAFE}'
        self.run_hook('echo "[]"', extra={'last_assistant_message': msg})
        self.assertEqual(len(self.calls('claim')), 1)
        self.assertEqual(len(self.calls('comment')), 1)

    def test_complete_line_in_the_message_is_applied_by_the_gate(self):
        self.claim_five_via_block()
        msg = f'Report.\n[complete 5 | sha={self.sha[:9]} tests="none: no code" docs="none: no docs" | Fixed it]\n{DONE}'
        proc = self.run_hook(self.dibs_claims_stub(), extra={'last_assistant_message': msg})
        out = json.loads(proc.stdout)
        self.assertNotIn('decision', out)
        self.assertIn('done 5: completed', out['systemMessage'])
        self.assertEqual(self.dbs()['issues']['5']['state'], 'CLOSED')

    def test_complete_line_refusal_blocks_once_and_not_when_stop_hook_active(self):
        self.claim_five_via_block()
        msg = f'Report.\n[complete 5 | sha=deadbeef1 | Fixed it]\n{DONE}'
        out = json.loads(self.run_hook(self.dibs_claims_stub(), extra={'last_assistant_message': msg}).stdout)
        self.assertEqual(out['decision'], 'block')
        self.assertIn('does not exist', out['reason'])
        again = self.run_hook(self.dibs_claims_stub(), extra={'last_assistant_message': msg, 'stop_hook_active': True})
        self.assertNotIn('decision', json.loads(again.stdout) if again.stdout.strip() else {})

    def test_dibs_block_refusal_blocks_once(self):
        msg = f'Report.\n```dibs\nnote 5: not mine\n```\n{SAFE}'
        out = json.loads(self.run_hook('echo "[]"', extra={'last_assistant_message': msg}).stdout)
        self.assertEqual(out['decision'], 'block')
        self.assertIn('not claimed by this session', out['reason'])

    def test_status_cases_with_no_claim_all_allow(self):
        for line in (SAFE, DONE, SAME, OTHER, ANDRES, WORK):
            with self.subTest(line=line):
                self.assertEqual(self.status_run(f'Report.\n{line}').stdout.strip(), '')

    def held_run(self, line, **extra):
        return self.run_hook('case "$*" in *"--held-by=sess-1"*) echo \'[{"issueId":7}]\';; *) echo "[]";; esac',
                             extra={'last_assistant_message': f'Report.\n{line}', **extra})

    def test_continue_in_this_session_and_waiting_keep_the_claim_without_blocking(self):
        for line in (SAME, ANDRES, WORK):
            with self.subTest(line=line):
                proc = self.held_run(line)
                self.assertEqual(proc.returncode, 0)
                self.assertNotIn('decision', json.loads(proc.stdout) if proc.stdout.strip() else {})

    def test_those_statuses_renew_the_lease_of_claims_made_through_the_block(self):
        self.claim_five_via_block()
        before = len(self.calls('heartbeat'))
        for line in (SAME, ANDRES, WORK):
            proc = self.run_hook(self.dibs_claims_stub(), extra={'last_assistant_message': f'Report.\n{line}'})
            self.assertNotIn('decision', json.loads(proc.stdout) if proc.stdout.strip() else {})
        self.assertEqual(len(self.calls('heartbeat')) - before, 3)
        self.assertIn('5', self.dbs()['claims'])

    def test_successful_note_with_continue_renews_the_held_claim(self):
        self.claim_five_via_block()
        before = len(self.calls('heartbeat'))
        msg = f'```dibs\nnote 5: still working\n```\n{SAME}'
        proc = self.run_hook(self.dibs_claims_stub(), extra={'last_assistant_message': msg})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn('decision', json.loads(proc.stdout) if proc.stdout.strip() else {})
        self.assertEqual(len(self.calls('comment')), 1)
        self.assertIn('5', self.dbs()['claims'])
        self.assertEqual(len(self.calls('heartbeat')) - before, 1)

    def test_safe_or_all_done_with_a_claim_open_blocks_asking_for_complete_or_release(self):
        for line in (SAFE, DONE):
            with self.subTest(line=line):
                out = json.loads(self.held_run(line).stdout)
                self.assertEqual(out['decision'], 'block')
                self.assertIn('task 7', out['reason'])
                self.assertIn('[complete', out['reason'])
                self.assertIn('todo_release', out['reason'])

    def test_different_session_with_a_claim_open_blocks_asking_for_a_handoff_and_release(self):
        out = json.loads(self.held_run(OTHER).stdout)
        self.assertEqual(out['decision'], 'block')
        self.assertIn('task 7', out['reason'])
        self.assertIn('handoff', out['reason'])
        self.assertIn('session-handoff', out['reason'])
        self.assertIn('todo_release', out['reason'])

    def spawned_run(self, line, sessions, claims='echo "[]"', **extra):
        reply = Path(self.tmp.name) / 'spawned.json'
        reply.write_text(json.dumps({'ok': True, 'sessions': sessions}))
        return self.run_hook(claims, env={'SESSIONEER_SPAWNED_CMD': f'cat {reply}'},
                             extra={'last_assistant_message': f'R.\n{line}', **extra})

    def test_completion_status_with_an_idle_spawn_blocks_naming_it(self):
        for line in (SAFE, DONE):
            with self.subTest(line=line):
                out = json.loads(self.spawned_run(line, [{'name': 'kid', 'status': 'idle'}]).stdout)
                self.assertEqual(out['decision'], 'block')
                self.assertIn('kid', out['reason'])
                self.assertIn('--reap', out['reason'])

    def test_working_blocked_and_archived_spawns_do_not_block(self):
        kids = [{'name': 'w', 'status': 'working'}, {'name': 'b', 'status': 'blocked'},
                {'name': 'a', 'status': 'idle', 'archived': True}]
        self.assertEqual(self.spawned_run(SAFE, kids).stdout.strip(), '')

    def test_non_completion_statuses_ignore_idle_spawns(self):
        for line in (SAME, OTHER, ANDRES, WORK):
            with self.subTest(line=line):
                self.assertEqual(self.spawned_run(line, [{'name': 'kid', 'status': 'idle'}]).stdout.strip(), '')

    def test_claim_and_idle_spawn_give_one_combined_message(self):
        out = json.loads(self.spawned_run(SAFE, [{'name': 'kid', 'status': 'idle'}], claims='echo \'[{"issueId": 7}]\'').stdout)
        self.assertEqual(out['decision'], 'block')
        for word in ('task 7', 'kid', '[complete', '--reap'):
            self.assertIn(word, out['reason'])

    def test_refused_spawn_lookup_does_not_block(self):
        self.assertEqual(self.run_hook('echo "[]"', extra={'last_assistant_message': f'R.\n{SAFE}'}).stdout.strip(), '')

    def test_stop_hook_active_with_an_idle_spawn_allows_with_a_warning(self):
        out = json.loads(self.spawned_run(SAFE, [{'name': 'kid', 'status': 'idle'}], stop_hook_active=True).stdout)
        self.assertNotIn('decision', out)
        self.assertIn('kid', out['systemMessage'])

    def test_claim_check_passes_the_session_id(self):
        args = Path(self.tmp.name) / 'args'
        proc = self.run_hook(f'echo "$@" > {args}; echo "[]"', extra={'last_assistant_message': f'R.\n{SAFE}'})
        self.assertEqual(proc.returncode, 0)
        self.assertIn('--held-by=sess-1', args.read_text())

    def test_stop_hook_active_with_the_claim_still_open_allows_with_a_warning(self):
        for line in (SAFE, DONE, OTHER):
            with self.subTest(line=line):
                out = json.loads(self.held_run(line, stop_hook_active=True).stdout)
                self.assertNotIn('decision', out)
                self.assertTrue(out['systemMessage'])

    def test_it_blocks_every_turn_there_is_no_cap(self):
        for _ in range(4):
            self.assertEqual(json.loads(self.held_run(SAFE).stdout)['decision'], 'block')

    def test_the_old_cap_setting_has_no_effect(self):
        capped = self.run_hook(self.HELD, env={'STOP_GATE_CAP': '0'}, extra={'last_assistant_message': f'R.\n{SAFE}'})
        self.assertEqual(json.loads(capped.stdout)['decision'], 'block')
        self.assertNotIn('cap (', capped.stdout)

    def test_the_last_status_phrase_in_the_last_three_lines_decides(self):
        out = self.held_run(f'{SAFE}\n{SAME}')
        self.assertNotIn('decision', json.loads(out.stdout) if out.stdout.strip() else {})
        out = json.loads(self.held_run(f'{SAME}\n{DONE}').stdout)
        self.assertEqual(out['decision'], 'block')
        out = json.loads(self.held_run(f'{ANDRES}\n{OTHER}').stdout)
        self.assertEqual(out['decision'], 'block')
        self.assertIn('handoff', out['reason'])

    def test_a_stale_counter_file_from_the_old_gate_is_ignored(self):
        state = Path(self.tmp.name) / 'state'
        state.mkdir()
        (state / 'sess-1').write_text('9')
        self.assertEqual(json.loads(self.held_run(SAFE).stdout)['decision'], 'block')

    def test_override_skips_the_gate(self):
        proc = self.run_hook(self.HELD, env={'DIBS_STOP_GATE': 'off'})
        self.assertEqual((proc.returncode, proc.stdout.strip()), (0, ''))

    def test_override_skips_the_status_and_claim_checks_but_still_applies_the_block(self):
        msg = 'Done.\n```dibs\nclaim 5\n```'
        proc = self.run_hook(self.HELD, env={'DIBS_STOP_GATE': 'off'}, extra={'last_assistant_message': msg})
        self.assertNotIn('decision', json.loads(proc.stdout) if proc.stdout.strip() else {})
        self.assertEqual(len(self.calls('claim')), 1)

    def test_allows_with_a_warning_when_dibs_is_unreachable(self):
        proc = self.run_hook('exit 1')
        self.assertEqual(proc.returncode, 0)
        out = json.loads(proc.stdout)
        self.assertNotIn('decision', out)
        self.assertIn('skipped', out['systemMessage'])

    def test_unreachable_dibs_with_a_closing_status_allows_with_a_warning(self):
        proc = self.run_hook('exit 1', extra={'last_assistant_message': f'R.\n{SAFE}'})
        self.assertEqual(proc.returncode, 0)
        out = json.loads(proc.stdout)
        self.assertNotIn('decision', out)
        self.assertIn('skipped', out['systemMessage'])

    def test_allows_with_a_warning_on_an_unreadable_answer(self):
        out = json.loads(self.run_hook('echo "not json"').stdout)
        self.assertNotIn('decision', out)
        self.assertIn('skipped', out['systemMessage'])


def prompt(text='go', **extra):
    return {'type': 'user', 'message': {'content': text}, **extra}


def use(name, ident='t1', **args):
    return {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'id': ident, 'name': name, 'input': args}]}}


def result(ident='t1', content='ok', error=False):
    return {'type': 'user', 'message': {'content': [
        {'type': 'tool_result', 'tool_use_id': ident, 'content': content, 'is_error': error}]}}


def bash(command, **outcome):
    return [use('Bash', command=command), result(**outcome)]


ASKED = [use('AskUserQuestion', 'q1'), result('q1')]


class LaunchOfferTest(unittest.TestCase):
    """"Continue in a different session" needs a question this turn or a launch in this session."""

    setUp = StopGateTest.setUp
    run_hook = StopGateTest.run_hook

    def stop(self, entries, status=OTHER, claims='echo "[]"', env=None, **extra):
        path = Path(self.tmp.name) / 'transcript.jsonl'
        path.write_text(''.join(json.dumps(e, separators=(',', ':')) + '\n' for e in entries))
        proc = self.run_hook(claims, env={'DIBS_LESSON_PROMPT': 'off', **(env or {})},
                             extra={'last_assistant_message': 'Report.\n' + status, 'transcript_path': str(path), **extra})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout) if proc.stdout.strip() else {}

    def assert_blocked(self, entries, msg=None):
        out = self.stop(entries)
        self.assertEqual(out.get('decision'), 'block', msg)
        for part in ('AskUserQuestion', 'launch now', 'sessioneer --rotate'):
            self.assertIn(part, out['reason'])

    def test_blocks_a_plain_text_proposal(self):
        self.assert_blocked([prompt(), *bash('git status')])

    def test_allows_after_a_question_in_this_turn(self):
        self.assertEqual(self.stop([prompt(), *ASKED]), {})

    def test_hook_feedback_and_task_notifications_do_not_end_the_turn(self):
        noise = [prompt('Stop hook feedback: x', isMeta=True), prompt('<task-notification>', origin={'kind': 'task-notification'})]
        self.assertEqual(self.stop([prompt(), *ASKED, *noise]), {})

    def test_a_question_from_an_earlier_turn_or_a_subagent_does_not_count(self):
        self.assert_blocked([prompt(), *ASKED, prompt('next')])
        self.assert_blocked([prompt(), {**use('AskUserQuestion'), 'isSidechain': True}])

    def test_allows_after_a_launch_anywhere_in_the_session(self):
        for command in ('sessioneer --rotate --handoff 12', 'cd /x && sessioneer --rotate --plan 3 --tag "a,b"',
                        'sessioneer --workdir /x --set-name "[worker] y" "do; the thing"',
                        'X=1 timeout 60 sessioneer \\\n  --rotate --prompt "$(cat /x)"', 'sessioneer --usage\nsessioneer --rotate --plan 3',
                        "cat > f <<'EOF'\nit's the brief\nEOF\nsessioneer --workdir /x - < f",
                        'for s in 1 2; do sessioneer --workdir /x "go $s"; done',
                        'sessioneer --rotate --prompt "$(cat <<EOF\nit\'s \"quoted\"\nEOF\n)"'):
            with self.subTest(command=command):
                self.assertEqual(self.stop([prompt(), *bash(command), prompt('next')]), {})

    def test_allows_after_an_auto_continued_receiver(self):
        command = 'sessioneer --next --plan 3 --post --no-gates'
        self.assertEqual(self.stop([prompt(), *bash(command, content='auto-continued: kid')]), {})
        self.assert_blocked([prompt(), *bash(command, content='offer posted')])

    def test_things_that_are_not_a_launch_still_block(self):
        for command in ('sessioneer --rotate --plan 3 --dry-run', 'grep -n "sessioneer --rotate" README.md',
                        'sessioneer --send peer "run --rotate"', 'sessioneer --offer --plan 3', 'echo sessioneer --rotate',
                        "cat > job <<'EOF'\nsessioneer --workdir /x go\nEOF"):
            with self.subTest(command=command):
                self.assert_blocked([prompt(), *bash(command)])

    def test_a_failed_or_unanswered_launch_blocks(self):
        self.assert_blocked([prompt(), *bash('sessioneer --rotate --plan 3', error=True)])
        self.assert_blocked([prompt(), use('Bash', command='sessioneer --rotate --plan 3')])

    def test_unreadable_transcript_allows(self):
        extra = {'last_assistant_message': OTHER}
        for path in (self.tmp.name, str(Path(self.tmp.name) / 'absent'), None):
            with self.subTest(path=path):
                proc = self.run_hook('echo "[]"', env={'DIBS_LESSON_PROMPT': 'off'},
                                     extra={**extra, **({'transcript_path': path} if path else {})})
                self.assertEqual((proc.returncode, proc.stdout.strip()), (0, ''))
        junk = Path(self.tmp.name) / 'junk'
        junk.write_bytes(b'\xff not json\n[1]\n')
        proc = self.run_hook('echo "[]"', env={'DIBS_LESSON_PROMPT': 'off'}, extra={**extra, 'transcript_path': str(junk)})
        self.assertEqual((proc.returncode, proc.stdout.strip()), (0, ''))

    def test_stop_hook_active_does_not_block_again(self):
        self.assertEqual(self.stop([prompt()], stop_hook_active=True), {})

    def test_other_statuses_need_no_offer(self):
        for status in (SAFE, DONE, SAME, ANDRES, WORK):
            self.assertEqual(self.stop([prompt()], status=status), {}, status)

    def test_gate_off_needs_no_offer(self):
        self.assertEqual(self.stop([prompt()], env={'DIBS_STOP_GATE': 'off'}), {})

    def test_joins_the_claim_and_lesson_messages(self):
        out = self.stop([prompt(), use('Edit')], claims='echo \'[{"issueId":7}]\'', env={'DIBS_LESSON_PROMPT': ''})
        for part in ('task 7', 'handoff', 'AskUserQuestion whether to launch', 'Lesson check'):
            self.assertIn(part, out['reason'])
        out = self.stop([prompt(), use('Edit')], env={'DIBS_LESSON_PROMPT': ''}, session_id='sess-2')
        for part in ('AskUserQuestion whether to launch', 'Lesson check'):
            self.assertIn(part, out['reason'])

    def test_unreachable_dibs_still_asks_for_the_offer(self):
        out = self.stop([prompt()], claims='exit 1')
        self.assertEqual(out['decision'], 'block')
        self.assertIn('skipped', out['systemMessage'])


class LessonPromptTest(unittest.TestCase):
    """The once-per-session lesson check on a completion status."""

    setUp = StopGateTest.setUp
    run_hook = StopGateTest.run_hook
    WORKED = '{"type":"assistant","message":{"content":[{"type":"tool_use","id":"t1","name":"Edit","input":{}}]}}'
    HELD = 'echo \'[{"issueId":5}]\''

    def stop(self, status=SAFE, transcript=WORKED, claims='echo "[]"', env=None, **extra):
        path = Path(self.tmp.name) / 'transcript.jsonl'
        if transcript is not None:
            path.write_text(transcript + '\n')
        proc = self.run_hook(claims, env=env, extra={'last_assistant_message': 'Report.\n' + status,
                                                     'transcript_path': str(path), **extra})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout) if proc.stdout.strip() else {}

    def test_asks_once_per_session_on_a_completion_status(self):
        out = self.stop()
        self.assertEqual(out['decision'], 'block')
        for part in ('Lesson check', 'todo_search', 'labels lesson, draft', 'trigger <key>', 'status line'):
            self.assertIn(part, out['reason'])
        self.assertEqual(self.stop(), {})
        self.assertEqual(self.stop(DONE), {})
        self.assertEqual(self.stop(session_id='sess-2')['decision'], 'block')

    def test_each_completion_status_asks_even_on_a_repeated_stop(self):
        for n, status in enumerate((SAFE, DONE, OTHER)):
            out = self.stop(status, stop_hook_active=True, session_id=f's{n}')
            self.assertIn('Lesson check', out.get('reason', ''), status)

    def test_waiting_statuses_do_not_ask_or_use_up_the_question(self):
        for status in (SAME, ANDRES, WORK):
            self.assertEqual(self.stop(status), {}, status)
        self.assertEqual(self.stop()['decision'], 'block')

    def test_work_signals(self):
        signals = ['"name":"Write"', '"name":"MultiEdit"', '"name":"NotebookEdit"', '"name":"mcp__dibs__todo_claim"',
                   '"name":"mcp__dibs__todo_complete"', '"is_error":true']
        for n, signal in enumerate(signals):
            self.assertIn('decision', self.stop(transcript='{%s}' % signal, session_id=f'sig{n}'), signal)

    def test_a_session_without_work_is_not_asked(self):
        quiet = ('{"name":"Read"}', '{"name":"mcp__dibs__todo_show","is_error":false}',
                 json.dumps({'text': 'the transcript says "name":"Edit" and "is_error":true'}))
        for transcript in quiet:
            self.assertEqual(self.stop(transcript=transcript), {}, transcript)

    def test_missing_transcript_is_not_asked(self):
        self.assertEqual(self.stop(transcript=None), {})
        proc = self.run_hook('echo "[]"', extra={'last_assistant_message': SAFE})
        self.assertEqual(proc.stdout.strip(), '')

    def test_switched_off(self):
        self.assertEqual(self.stop(env={'DIBS_LESSON_PROMPT': 'off'}), {})
        self.assertEqual(self.stop(env={'DIBS_STOP_GATE': 'off'}), {})

    def test_unwritable_state_dir_never_blocks(self):
        blocker = Path(self.tmp.name) / 'file'
        blocker.write_text('')
        self.assertEqual(self.stop(env={'STOP_GATE_STATE_DIR': str(blocker / 'state')}), {})

    def test_joins_the_claim_problem_in_one_message(self):
        out = self.stop(claims=self.HELD)
        self.assertIn('holds task 5', out['reason'])
        self.assertIn('Lesson check', out['reason'])
        again = self.stop(claims=self.HELD)
        self.assertIn('holds task 5', again['reason'])
        self.assertNotIn('Lesson check', again['reason'])

    def test_unreachable_dibs_does_not_ask(self):
        self.assertNotIn('decision', self.stop(claims='exit 1'))


if __name__ == '__main__':
    unittest.main()
