"""Work line protocol: dibs-block.py guard reads `[work ...]` lines from the transcript, claims, delivers rules by type,
denies changes without a claim, waits for the transcript. Only against a fake Dibs CLI, temp dirs and temp rule files."""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dibs_tracking_hook import STUB  # noqa: E402

HOOK = Path(__file__).resolve().parents[1] / 'ai/hooks/dibs-block.py'
LATE = 'This rule arrived after the call ran. Check that call and your earlier work in this session against it, and fix what it missed.'
TYPES = ('code', 'tests', 'docs', 'git', 'db', 'live-site', 'dibs', 'infra', 'research')
TYPE_KEYS = {'code': ['live-repo'], 'tests': ['test-file', 'test-run'], 'docs': ['md-edit', 'project-doc'],
             'git': ['git-commit', 'git-history', 'git-add-all', 'git-push'], 'db': ['db-cli'],
             'live-site': ['live-check', 'live-repo'],
             'dibs': ['dibs-create', 'dibs-revise', 'dibs-comment', 'dibs-claim', 'dibs-complete', 'dibs-release'],
             'infra': ['home-net', 'schedule', 'live-check'], 'research': []}
KEYS = sorted({k for v in TYPE_KEYS.values() for k in v})
KEY_ID = {k: 5000 + i for i, k in enumerate(KEYS)}
EXPORT = ''.join(f'## {i}@1 Rule: {k}\nTEXT-{k}\n' for k, i in KEY_ID.items())
NEW = '103'  # the fake CLI numbers new issues 100 + count of existing ones (5, 6, 7 are seeded)
OPEN = {'state': 'OPEN', 'body': '', 'revision': 1}


def text_entry(*texts):
    return {'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': t} for t in texts]}}


def tool_entry(tid, name='Bash', inp=None):
    return {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'id': tid, 'name': name, 'input': inp or {}}]}}


class WorkBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='/var/tmp')  # outside /tmp: /tmp edits are exempt
        self.addCleanup(self.tmp.cleanup)
        self.root = root = Path(self.tmp.name)
        self.repo = root / 'repo'
        self.repo.mkdir()
        subprocess.run(['git', '-C', str(self.repo), 'init', '-q', '-b', 'work-test'], check=True)
        (self.repo / 'changed.txt').write_text('wip')
        stub = root / 'stub.py'
        stub.write_text(STUB)
        self.db = root / 'db.json'
        self.db.write_text(json.dumps({'log': [], 'claims': {}, 'dropped': [], 'comments': {}, 'keys': {},
                                       'issues': {'5': {**OPEN, 'id': 5}, '7': {**OPEN, 'id': 7},
                                                  '6': {'id': 6, 'state': 'CLOSED', 'body': '', 'revision': 1}}}))
        (root / 'rules.md').write_text(EXPORT)
        (root / 'trig.json').write_text(json.dumps({k: [i] for k, i in KEY_ID.items()}))
        (root / 'xdg').mkdir()
        (root / 'home').mkdir()
        self.state = root / 'state'
        self.transcript = root / 'transcript.jsonl'
        self.transcript.write_text('')
        self.env = {**os.environ, 'DIBS_CLI': f'{sys.executable} {stub} {self.db}', 'DIBS_BLOCK_STATE_DIR': str(self.state),
                    'DIBS_AGENT_PID': '4242', 'DIBS_ATLAS_SYNC': 'off', 'SESSIONEER_SELF': 'tester',
                    'XDG_RUNTIME_DIR': str(root / 'xdg'), 'HOME': str(root / 'home'),
                    'RULE_FILES': str(root / 'rules.md'), 'RULE_TRIGGERS': str(root / 'trig.json'),
                    'RULE_STATE_DIR': str(root / 'rstate'), 'RULE_PRIVATE_KEYS': str(root / 'nokeys.json'),
                    'SESSIONEER_BIN': str(root / 'no-sessioneer'), 'DIBS_WORK_WAIT_SECONDS': '0.3'}
        self.n = 0

    def dbs(self):
        return json.loads(self.db.read_text())

    def update_db(self, **changes):
        db = self.dbs(); db.update(changes); self.db.write_text(json.dumps(db))

    def calls(self, command):
        return [c for c in self.dbs()['log'] if c[0] == command]

    def write_transcript(self, *entries, append=False):
        with open(self.transcript, 'a' if append else 'w') as f:
            for e in entries:
                f.write(json.dumps(e) + '\n')

    def say(self, *texts, append=False):
        """One assistant turn: the texts, then a tool_use. Returns the tool_use id to pass to the guard."""
        self.n += 1
        tid = f'toolu_{self.n}'
        self.write_transcript(text_entry(*texts), tool_entry(tid), append=append)
        return tid

    def payload(self, tool, inp, tid, **extra):
        return {'session_id': 'sess-1', 'cwd': str(self.repo), 'transcript_path': str(self.transcript),
                'tool_name': tool, 'tool_input': inp, 'tool_use_id': tid, **extra}

    def run_guard(self, tool, inp, tid='toolu_1', env=None, **extra):
        p = subprocess.run([sys.executable, str(HOOK), 'guard'], input=json.dumps(self.payload(tool, inp, tid, **extra)),
                           text=True, capture_output=True, env={**self.env, **(env or {})})
        self.assertEqual(p.returncode, 0, p.stderr)
        try:
            return json.loads(p.stdout) if p.stdout.strip() else None
        except json.JSONDecodeError:
            self.fail(f'Non-JSON hook stdout: {p.stdout!r}')

    def hook(self, mode, env=None, **data):
        p = subprocess.run([sys.executable, str(HOOK), mode], input=json.dumps({'session_id': 'sess-1', 'cwd': str(self.repo), **data}),
                           text=True, capture_output=True, env={**self.env, **(env or {})})
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(p.stdout) if p.stdout.strip() else None

    def read(self, tid='toolu_1', **kw):
        return self.run_guard('Read', {'file_path': str(self.repo / 'changed.txt')}, tid, **kw)

    def touch(self, tid='toolu_1', **kw):
        return self.run_guard('Bash', {'command': 'touch f'}, tid, **kw)

    def edit(self, tid='toolu_1', **kw):
        return self.run_guard('Edit', {'file_path': str(self.repo / 'changed.txt')}, tid, **kw)

    def ev(self, out):
        return out.get('hookSpecificOutput', {})

    def assert_denied(self, out):
        self.assertIsNotNone(out)
        self.assertEqual(self.ev(out)['permissionDecision'], 'deny')
        return self.ev(out)['permissionDecisionReason']

    def assert_not_denied(self, out):
        if out:
            self.assertNotEqual(self.ev(out).get('permissionDecision'), 'deny')

    def assert_nothing_happened(self):
        self.assertEqual(self.calls('claim'), [])
        self.assertEqual(self.calls('create'), [])
        self.assertEqual(self.dbs()['claims'], {})

    def assert_made_from_line(self, description):
        create = ' '.join(self.calls('create')[0])
        self.assertIn(description, create)
        self.assertNotIn('Auto-tracked', create)

    def held(self):
        return set(self.dbs()['claims'])


class ReviewRegressionTest(WorkBase):
    def test_same_call_rule_injection_cannot_bypass_first_mutation_hold(self):
        ids = [740, 741, 742]
        (self.root / 'rules.md').write_text(''.join(f'## {i}@1 Rule: test\nTEXT-{i}\n' for i in ids))
        (self.root / 'trig.json').write_text(json.dumps({'test-file': ids, 'test-run': ids}))
        tid = self.say('[work 5 | tests | tests]')
        inp = {'command': 'pytest; touch f'}
        event = {**self.payload('Bash', inp, tid), 'hook_event_name': 'PreToolUse'}
        rule_hook = HOOK.parent / 'rule-inject.py'
        proc = subprocess.run([sys.executable, str(rule_hook)], input=json.dumps(event),
                              text=True, capture_output=True, env=self.env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('TEXT-740', proc.stdout)
        reason = self.assert_denied(self.run_guard('Bash', inp, tid))
        for rule_id in ids:
            self.assertIn(f'TEXT-{rule_id}', reason)
        self.assertIn('retry', reason.lower())
        self.assertNotIn(LATE, reason)
        self.assertEqual(self.held(), {'5'})

    def test_refused_work_line_does_not_starve_corrected_line(self):
        tid = self.say('[work 6 | closed | research]')
        self.assert_not_denied(self.read(tid))
        self.assertEqual(self.held(), set())
        tid = self.say('[work 5 | corrected | research]', append=True)
        self.assert_not_denied(self.touch(tid))
        self.assertEqual(self.held(), {'5'})

    def test_four_backtick_fence_with_inner_triples_never_claims(self):
        tid = self.say('````markdown\n```text\n[work 5 | example only | research]\n```\n````')
        self.assertIsNone(self.read(tid))
        self.assert_nothing_happened()

    def test_delayed_unclaimed_read_without_work_is_silent_and_makes_no_cli_calls(self):
        tid = 'toolu_delayed'
        timer = threading.Timer(0.1, lambda: self.write_transcript(text_entry('Ordinary read.'), tool_entry(tid)))
        timer.start()
        self.addCleanup(timer.join)
        self.assertIsNone(self.read(tid))
        self.assertEqual(self.dbs()['log'], [])


class WorkLineClaimTest(WorkBase):
    # intent: contract 1, id and new lines are processed by the guard in the same hook call, once, in order.
    def test_id_line_on_a_read_claims_allows_and_delivers_rules_with_late_notice(self):
        tid = self.say('Starting.', '[work 5 | Fix the parser | code]')
        out = self.read(tid)
        event = self.ev(out)
        self.assertEqual((event['hookEventName'], event['permissionDecision']), ('PreToolUse', 'allow'))
        ctx = event['additionalContext']
        self.assertIn('5', ctx)
        self.assertIn('TEXT-live-repo', ctx)
        self.assertTrue(ctx.endswith(LATE))
        self.assertEqual(self.held(), {'5'})
        claim = self.calls('claim')
        self.assertEqual(len(claim), 1)
        self.assertIn('--path=' + str(self.repo), claim[0])
        self.assertIn('--agent=claude:tester:sess-1', claim[0])
        self.assertEqual(self.calls('create'), [])
        crumb = json.loads((self.state / 'sess-1.json').read_text())['breadcrumb']
        self.assertEqual((crumb['cwd'], crumb['branch'], crumb['pid']), (str(self.repo), 'work-test', 4242))

    def test_new_line_creates_a_temporary_task_titled_with_the_description_and_claims_it(self):
        tid = self.say('[work new | Rework the importer | code+tests]')
        out = self.read(tid)
        self.assertIn(NEW, self.ev(out)['additionalContext'])
        token = json.loads((self.state / 'sess-1.json').read_text())['claims'][str(NEW)]
        self.assertIn('Capability token for MCP calls on this claim', self.ev(out)['additionalContext'])
        self.assertIn(token, self.ev(out)['additionalContext'])
        create = self.calls('create')
        self.assertEqual(len(create), 1)
        self.assertIn('--temporary', create[0])
        joined = ' '.join(create[0])
        self.assertIn('Rework the importer', joined)
        self.assertNotIn('Auto-tracked', joined)
        self.assertIn(str(self.repo), joined)
        self.assertIn('code+tests', joined)
        self.assertTrue(any(a.startswith('--idempotency-key=') for a in create[0]))
        self.assertTrue(self.dbs()['issues'][NEW]['temporary'])
        self.assertEqual(self.held(), {NEW})
        self.assertIn('--path=' + str(self.repo), self.calls('claim')[0])

    def test_combined_types_deliver_the_union_of_rules_once(self):
        tid = self.say('[work 5 | Mixed | code+tests+live-site]')
        ctx = self.ev(self.read(tid))['additionalContext']
        for key in ('live-repo', 'test-file', 'test-run', 'live-check'):
            self.assertEqual(ctx.count(f'TEXT-{key}'), 1, key)
        self.assertNotIn('TEXT-db-cli', ctx)

    def test_every_valid_type_is_accepted(self):
        for index, kind in enumerate(TYPES):
            with self.subTest(kind=kind):
                self.say(f'[work new | Task {index} | {kind}]', append=index > 0)
                self.read(f'toolu_{index + 1}')
                self.assertEqual(len(self.calls('create')), index + 1)

    def test_line_with_trailing_whitespace_in_the_middle_of_prose_fires(self):
        tid = self.say('Some intro.\n\n[work 5 | Fix it | code]   \n\nMore prose.')
        self.read(tid)
        self.assertEqual(self.held(), {'5'})

    def test_line_in_an_earlier_text_block_of_the_same_turn_fires(self):
        self.write_transcript(text_entry('thinking out loud'), text_entry('[work 5 | Fix | code]'), tool_entry('toolu_9'))
        self.read('toolu_9')
        self.assertEqual(self.held(), {'5'})

    def test_closed_or_unknown_task_is_refused_without_crashing(self):
        for task in ('6', '999'):
            with self.subTest(task=task):
                tid = self.say(f'[work {task} | Nope | code]')
                self.assert_not_denied(self.read(tid))
                self.assertEqual(self.dbs()['claims'], {})

    def test_already_held_task_is_not_claimed_twice(self):
        self.update_db(claims={'5': {'token': 'tok5', 'agent': 'claude:tester:sess-1'}})
        tid = self.say('[work 5 | Again | code]')
        self.assert_not_denied(self.read(tid))
        self.assertEqual(self.calls('claim'), [])

    def test_lines_are_processed_in_transcript_order(self):
        tid = self.say('[work 5 | First | docs]', '[work new | Second | research]')
        self.read(tid)
        names = [c[0] for c in self.dbs()['log'] if c[0] in ('claim', 'create')]
        self.assertEqual(names, ['claim', 'create', 'claim'])
        self.assertEqual(self.held(), {'5', NEW})

    def test_a_line_is_never_processed_twice_and_new_lines_are_picked_up(self):
        tid = self.say('[work new | Once | research]')
        self.read(tid)
        self.read(tid)
        self.edit(tid)
        self.assertEqual((len(self.calls('create')), len(self.calls('claim'))), (1, 1))
        tid2 = self.say('[work 5 | Later | research]', append=True)
        self.read(tid2)
        self.assertEqual(self.held(), {NEW, '5'})
        self.assertEqual(len(self.calls('claim')), 2)

    def test_replay_after_state_loss_does_not_create_a_second_task(self):
        tid = self.say('[work new | Replayed | research]')
        self.read(tid)
        self.update_db(claims={})
        for f in self.state.glob('*.json'):
            f.unlink()
        self.read(tid)
        self.assertEqual(len(self.dbs()['issues']) - 3, 1)
        keys = [next(a for a in c if a.startswith('--idempotency-key=')) for c in self.calls('create')]
        self.assertEqual(len(set(keys)), 1)

    def test_two_new_lines_get_different_idempotency_keys(self):
        tid = self.say('[work new | One | research]', '[work new | Two | research]')
        self.read(tid)
        self.assertEqual(len(self.calls('create')), 2)
        keys = [next(a for a in c if a.startswith('--idempotency-key=')) for c in self.calls('create')]
        self.assertEqual(len(set(keys)), 2)

    def test_dry_run_does_nothing(self):
        tid = self.say('[work new | Dry | code]')
        self.assertIsNone(self.touch(tid, env={'DIBS_BLOCK_DRY_RUN': '1'}))
        self.assertEqual(self.dbs()['log'], [])


class WorkLineParsingTest(WorkBase):
    # intent: contract 1, only a bare line in an assistant text block outside code fences fires; reads then stay silent.
    def silent(self, *texts, entries=None):
        if entries is not None:
            self.write_transcript(*entries, tool_entry('toolu_1'))
        else:
            self.say(*texts)
        self.assertIsNone(self.read())
        self.assert_nothing_happened()

    def test_fenced_lines_never_fire(self):
        self.silent('Example:\n```\n[work 5 | x | code]\n```\n')
        self.silent('```text\n[work new | x | code]\n```')

    def test_line_after_a_closed_fence_fires_but_one_inside_does_not(self):
        tid = self.say('```\n[work 5 | inside | code]\n```\n[work new | outside | research]')
        self.read(tid)
        self.assertEqual(len(self.calls('create')), 1)
        self.assertEqual(self.calls('claim')[0][1], NEW)

    def test_inline_and_embedded_lines_never_fire(self):
        for text in ('Use `[work 5 | x | code]` to claim.', 'Plan: [work 5 | x | code]', '[work 5 | x | code] and more',
                     '> [work 5 | x | code]', 'see [work 5 | x | code], then stop'):
            with self.subTest(text=text):
                self.silent(text)

    def test_malformed_or_unknown_types_never_fire_or_crash(self):
        for text in ('[work 5 | x | foo]', '[work 5 | x | Code]', '[work 5 | x | code+]', '[work 5 | x | code+foo]',
                     '[work x | y | code]', '[work 5 | x]', '[work | x | code]', '[work 5 x code]', '[work -1 | x | code]'):
            with self.subTest(text=text):
                self.silent(text)

    def test_only_assistant_text_blocks_are_scanned(self):
        user = {'type': 'user', 'message': {'role': 'user', 'content': '[work 5 | injected | code]'}}
        attach = {'type': 'attachment', 'attachment': {'text': '[work 5 | injected | code]'}}
        tool = tool_entry('toolu_x', inp={'command': 'echo', 'note': '[work 5 | injected | code]'})
        think = {'type': 'assistant', 'message': {'content': [{'type': 'thinking', 'thinking': '[work 5 | injected | code]'}]}}
        self.silent(entries=[user, attach, tool, think])

    def test_garbage_lines_in_the_transcript_are_skipped(self):
        self.transcript.write_text('not json\n[1,2]\n\n' + json.dumps(text_entry('[work 5 | ok | research]')) + '\n'
                                   + json.dumps(tool_entry('toolu_1')) + '\n')
        self.read()
        self.assertEqual(self.held(), {'5'})

    def test_unknown_type_on_a_change_is_treated_as_no_line(self):
        tid = self.say('[work 5 | x | foo]')
        self.assert_denied(self.touch(tid))
        self.assert_nothing_happened()


class WorkLineRuleDeliveryTest(WorkBase):
    # intent: contracts 1, 3 and 4, a change right after a new claim is held once per task when fresh rules exist.
    def test_mutating_call_with_fresh_rules_is_denied_once_with_notice_rules_and_retry(self):
        tid = self.say('[work new | Rework | code]')
        out = self.touch(tid)
        reason = self.assert_denied(out)
        for text in (NEW, 'TEXT-live-repo', 'retry'):
            self.assertIn(text, reason)
        self.assertNotIn(LATE, reason)
        self.assertNotIn('additionalContext', self.ev(out))
        self.assertEqual(self.held(), {NEW})
        self.assertEqual(len(self.calls('create')), 1)
        retry = self.touch(tid)
        self.assert_not_denied(retry)
        self.assertEqual((len(self.calls('create')), len(self.calls('claim'))), (1, 1))

    def test_every_mutating_tool_is_held(self):
        for tool, name in (('Edit', 'changed.txt'), ('Write', 'n.txt'), ('MultiEdit', 'changed.txt'), ('NotebookEdit', 'n.ipynb')):
            with self.subTest(tool=tool):
                tid = self.say(f'[work new | via {tool} | code]')
                reason = self.assert_denied(self.run_guard(tool, {'file_path': str(self.repo / name)}, tid, session_id=f's-{tool}'))
                self.assertIn('TEXT-live-repo', reason)

    def test_hold_happens_once_per_task_but_again_for_a_new_task(self):
        tid = self.say('[work 5 | One | code]')
        self.assert_denied(self.touch(tid))
        tid2 = self.say('[work 5 | Same task, other type | tests]', append=True)
        self.assert_not_denied(self.touch(tid2))
        tid3 = self.say('[work 7 | Other task | docs]', append=True)
        reason = self.assert_denied(self.touch(tid3))
        self.assertIn('TEXT-md-edit', reason)
        self.assertIn('7', reason)

    def test_rules_already_delivered_mean_no_hold(self):
        tid = self.say('[work 5 | Read first | code]')
        self.assertIn('TEXT-live-repo', self.ev(self.read(tid))['additionalContext'])
        tid2 = self.say('[work 7 | Now change | code]', append=True)
        out = self.touch(tid2)
        self.assert_not_denied(out)
        self.assertEqual(self.held(), {'5', '7'})
        self.assertIn('7', self.ev(out)['additionalContext'])
        self.assertNotIn('TEXT-live-repo', self.ev(out)['additionalContext'])

    def test_type_without_rules_is_allowed_with_the_claim_notice_and_no_late_notice(self):
        tid = self.say('[work new | Look around | research]')
        out = self.touch(tid)
        self.assert_not_denied(out)
        ctx = self.ev(out)['additionalContext']
        self.assertIn(NEW, ctx)
        self.assertNotIn(LATE, ctx)
        self.assert_made_from_line('Look around')
        self.assertNotIn('TEXT-', ctx)

    def test_each_type_delivers_exactly_its_keys(self):
        for kind in TYPES:
            with self.subTest(kind=kind):
                tid = self.say(f'[work new | t {kind} | {kind}]')
                out = self.read(tid, session_id=f'ty-{kind}')
                ctx = self.ev(out)['additionalContext']
                self.assertEqual({k for k in KEYS if f'TEXT-{k}' in ctx}, set(TYPE_KEYS[kind]))

    def test_read_only_bash_with_a_line_is_allowed_with_context(self):
        tid = self.say('[work 5 | Inspect | git]')
        out = self.run_guard('Bash', {'command': 'git status'}, tid)
        self.assertEqual(self.ev(out).get('permissionDecision'), 'allow')
        self.assertIn('TEXT-git-commit', self.ev(out)['additionalContext'])

    def test_mcp_tool_with_a_line_is_allowed(self):
        tid = self.say('[work 5 | Ask dibs | dibs]')
        out = self.run_guard('mcp__dibs__todo_show', {'ids': [5]}, tid)
        self.assertEqual(self.ev(out).get('permissionDecision'), 'allow')

    def test_scratch_path_edit_is_not_held(self):
        tid = self.say('[work 5 | Scratch | code]')
        out = self.run_guard('Write', {'file_path': '/tmp/scratch-xyz.txt'}, tid)
        self.assert_not_denied(out)

    def test_rule_delivery_is_shared_with_rule_inject(self):
        tid = self.say('[work 5 | Commit | git]')
        self.read(tid)
        # the guard marked them delivered, so rule-inject has nothing left to send for a commit
        rule_inject = Path(HOOK).with_name('rule-inject.py')
        p = subprocess.run([str(rule_inject)], text=True, capture_output=True, env=self.env,
                           input=json.dumps({'session_id': 'sess-1', 'hook_event_name': 'PreToolUse', 'tool_name': 'Bash',
                                             'tool_input': {'command': 'git commit -m x'}}))
        self.assertEqual(p.stdout.strip(), '')


class WorkLineWaitTest(WorkBase):
    # intent: contract 0, wait for the tool_use_id to land in the transcript, only without a claim, bounded by the cap.
    def popen(self, tool, inp, tid, env=None):
        return subprocess.Popen([sys.executable, str(HOOK), 'guard'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, env={**self.env, **(env or {})})

    def finish(self, proc, tool, inp, tid):
        out, err = proc.communicate(json.dumps(self.payload(tool, inp, tid)), timeout=20)
        self.assertEqual(proc.returncode, 0, err)
        return json.loads(out) if out.strip() else None

    def test_waits_for_a_late_transcript_and_then_sees_the_line(self):
        entries = [text_entry('[work new | Late | research]'), tool_entry('toolu_late')]

        def writer():
            time.sleep(0.4)
            self.transcript.write_text(''.join(json.dumps(e) + '\n' for e in entries))
        thread = threading.Thread(target=writer)
        env = {'DIBS_WORK_WAIT_SECONDS': '3'}
        start = time.time()
        proc = self.popen('Bash', {'command': 'touch f'}, 'toolu_late', env)
        thread.start()
        out = self.finish(proc, 'Bash', {'command': 'touch f'}, 'toolu_late')
        thread.join()
        self.assertLess(time.time() - start, 2.8)
        self.assert_not_denied(out)
        self.assertEqual(self.held(), {NEW})
        self.assert_made_from_line('Late')

    def test_a_transcript_that_already_has_the_entries_does_not_wait(self):
        tid = self.say('[work new | Ready | research]')
        start = time.time()
        self.touch(tid, env={'DIBS_WORK_WAIT_SECONDS': '10'})
        self.assertLess(time.time() - start, 4)
        self.assertEqual(self.held(), {NEW})
        self.assert_made_from_line('Ready')

    def test_a_held_claim_skips_the_wait(self):
        self.update_db(claims={'5': {'token': 'tok5', 'agent': 'claude:tester:sess-1'}})
        self.write_transcript(text_entry('nothing'))
        start = time.time()
        self.assertIsNone(self.touch('toolu_never', env={'DIBS_WORK_WAIT_SECONDS': '10'}))
        self.assertLess(time.time() - start, 4)

    def test_without_the_entry_it_waits_the_cap_then_scans_what_is_there(self):
        self.write_transcript(text_entry('[work new | Present | research]'), tool_entry('toolu_other'))
        start = time.time()
        self.touch('toolu_missing', env={'DIBS_WORK_WAIT_SECONDS': '0.6'})
        elapsed = time.time() - start
        self.assertGreaterEqual(elapsed, 0.55)
        self.assertLess(elapsed, 5)
        self.assertEqual(self.held(), {NEW})
        self.assert_made_from_line('Present')

    def test_missing_tool_use_id_scans_after_the_cap(self):
        self.write_transcript(text_entry('[work new | NoId | research]'), tool_entry('toolu_other'))
        p = subprocess.run([sys.executable, str(HOOK), 'guard'], text=True, capture_output=True, env=self.env,
                           input=json.dumps({'session_id': 'sess-1', 'cwd': str(self.repo), 'transcript_path': str(self.transcript),
                                             'tool_name': 'Bash', 'tool_input': {'command': 'touch f'}}))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(self.held(), {NEW})
        self.assert_made_from_line('NoId')

    def test_missing_unreadable_or_directory_transcript_means_no_line(self):
        for path in (None, str(self.root / 'nope.jsonl'), str(self.root)):
            with self.subTest(path=path):
                data = self.payload('Bash', {'command': 'touch f'}, 'toolu_1', session_id=f'tr-{path}')
                data.pop('transcript_path')
                if path:
                    data['transcript_path'] = path
                p = subprocess.run([sys.executable, str(HOOK), 'guard'], text=True, capture_output=True, env=self.env,
                                   input=json.dumps(data))
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertEqual(json.loads(p.stdout)['hookSpecificOutput']['permissionDecision'], 'deny')
        self.assert_nothing_happened()


class DenyWithoutClaimTest(WorkBase):
    # intent: contract 2, changes without a claim or work line are denied with an actionable reason, reads never.
    def silent_transcript(self):
        return self.say('Just thinking.')

    def test_change_is_denied_with_the_line_to_output_and_the_types(self):
        reason = self.assert_denied(self.touch(self.silent_transcript()))
        self.assertIn('[work', reason)
        self.assertIn('own line', reason)
        self.assertIn('code fence', reason)
        for kind in TYPES:
            self.assertIn(kind, reason)
        self.assert_nothing_happened()

    def test_every_edit_tool_is_denied_without_a_claim(self):
        tid = self.silent_transcript()
        for tool in ('Edit', 'Write', 'MultiEdit', 'NotebookEdit'):
            with self.subTest(tool=tool):
                self.assert_denied(self.run_guard(tool, {'file_path': str(self.repo / 'changed.txt')}, tid,
                                                  session_id=f's-{tool}'))

    def test_reads_and_searches_are_never_denied_even_after_denials(self):
        tid = self.silent_transcript()
        self.assert_denied(self.touch(tid))
        self.assert_denied(self.touch(tid))
        for tool, inp in (('Read', {'file_path': str(self.repo / 'changed.txt')}), ('Grep', {'pattern': 'x'}),
                          ('Glob', {'pattern': '*'}), ('WebSearch', {'query': 'x'}), ('WebFetch', {'url': 'https://example.test/'}),
                          ('Bash', {'command': 'git status'}), ('Bash', {'command': 'ls -la | wc -l'}),
                          ('Bash', {'command': 'rg "x;y" src'}), ('mcp__dibs__todo_list', {}),
                          ('mcp__playwright__browser_snapshot', {}), ('Task', {'prompt': 'x'}), ('TodoWrite', {'todos': []})):
            with self.subTest(tool=tool, inp=inp):
                self.assertIsNone(self.run_guard(tool, inp, tid))
        self.assert_nothing_happened()

    def test_reads_do_not_count_toward_the_two_denials(self):
        tid = self.silent_transcript()
        self.assert_denied(self.touch(tid))
        for _ in range(3):
            self.read(tid)
        self.assert_denied(self.touch(tid))
        self.assertEqual(self.calls('create'), [])

    def test_third_change_is_auto_tracked_allowed_with_a_visible_warning(self):
        self.hook('prompt', prompt='Repair the importer')
        tid = self.silent_transcript()
        self.assert_denied(self.touch(tid))
        self.assert_denied(self.touch(tid))
        out = self.touch(tid)
        self.assertEqual(self.ev(out).get('permissionDecision'), 'allow')
        self.assertIn('Dibs', out['systemMessage'])
        self.assertIn(NEW, self.ev(out)['additionalContext'])
        create = self.calls('create')
        self.assertEqual(len(create), 1)
        self.assertIn('Auto-tracked: Repair the importer', ' '.join(create[0]))
        self.assertIn('--temporary', create[0])
        self.assertEqual(self.held(), {NEW})
        self.assertIsNone(self.touch(tid))

    def test_a_claim_resets_the_denial_counter(self):
        tid = self.silent_transcript()
        self.assert_denied(self.touch(tid))
        tid2 = self.say('[work 5 | Claim now | research]', append=True)
        self.assert_not_denied(self.touch(tid2))
        self.update_db(claims={})
        self.assert_denied(self.touch(tid2))
        self.assert_denied(self.touch(tid2))
        self.assertEqual(self.calls('create'), [])
        self.assertEqual(self.ev(self.touch(tid2))['permissionDecision'], 'allow')
        self.assertEqual(len(self.calls('create')), 1)

    def test_denial_counters_are_per_session(self):
        tid = self.silent_transcript()
        self.assert_denied(self.touch(tid))
        self.assert_denied(self.touch(tid))
        self.assert_denied(self.touch(tid, session_id='sess-2'))

    def test_candidate_task_ids_from_the_prompt_are_named(self):
        for index, prompt in enumerate(('continue dibs 1577 please', 'resume task 1578', 'finish plan 1579', 'look at #1580')):
            with self.subTest(prompt=prompt):
                session = f'cand-{index}'
                self.hook('prompt', session_id=session, prompt=prompt)
                reason = self.assert_denied(self.touch(self.silent_transcript(), session_id=session))
                self.assertIn(str(1577 + index), reason)

    def test_no_candidates_are_named_for_a_prompt_without_ids(self):
        self.hook('prompt', prompt='Repair the importer 2024')
        reason = self.assert_denied(self.touch(self.silent_transcript()))
        self.assertNotIn('task 2024', reason)

    def test_subagent_calls_are_exempt(self):
        self.assertIsNone(self.touch(self.silent_transcript(), agent_id='agent-7'))
        self.assertEqual(self.dbs()['log'], [])

    def test_scratch_paths_are_exempt(self):
        tid = self.silent_transcript()
        xdg = self.env['XDG_RUNTIME_DIR']
        for tool, inp in (('Write', {'file_path': '/tmp/a.txt'}), ('Edit', {'file_path': xdg + '/x'}),
                          ('Bash', {'command': 'echo x > /dev/null'}), ('Bash', {'command': 'rm -rf /tmp/dir/y'})):
            with self.subTest(tool=tool, inp=inp):
                self.assertIsNone(self.run_guard(tool, inp, tid))

    def test_existing_live_claim_allows_changes_silently(self):
        self.update_db(claims={'5': {'token': 'external', 'agent': 'claude:tester:sess-1'}})
        self.assertIsNone(self.touch(self.silent_transcript()))
        self.assertIsNone(self.edit(self.silent_transcript()))
        self.assertEqual(self.calls('create'), [])

    def test_dibs_down_allows_with_a_warning_and_keeps_the_breadcrumb(self):
        failing = self.root / 'fail.py'
        failing.write_text('import sys\nprint("boom")\nsys.exit(1)\n')
        self.hook('prompt', prompt='Offline work')
        for cli in (f'{sys.executable} {failing}', '/nonexistent/dibs'):
            with self.subTest(cli=cli):
                out = self.touch(self.silent_transcript(), env={'DIBS_CLI': cli})
                self.assertIsNotNone(out)
                self.assertNotEqual(self.ev(out).get('permissionDecision'), 'deny')
                self.assertIn('Dibs', out['systemMessage'])
        self.assertEqual(json.loads((self.state / 'sess-1.json').read_text())['breadcrumb']['prompt'], 'Offline work')

    def test_missing_session_id_and_unusable_state_dir_allow(self):
        tid = self.silent_transcript()
        self.assert_not_denied(self.touch(tid, session_id=''))
        blocker = self.root / 'a-file'
        blocker.write_text('x')
        self.assert_not_denied(self.touch(tid, env={'DIBS_BLOCK_STATE_DIR': str(blocker)}))

    def test_unreadable_claims_answer_allows(self):
        self.update_db(unreadable=True)
        self.assert_not_denied(self.touch(self.silent_transcript()))

    def test_dry_run_never_denies(self):
        self.assertIsNone(self.touch(self.silent_transcript(), env={'DIBS_BLOCK_DRY_RUN': '1'}))

    def test_invalid_json_payload_is_not_denied(self):
        p = subprocess.run([sys.executable, str(HOOK), 'guard'], input='{nope', text=True, capture_output=True, env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertNotIn('"deny"', p.stdout)


class TemporaryTaskSurvivalTest(WorkBase):
    # intent: contract 7, a `new` task outlives a dead session and is findable by path; nothing closes it.
    def test_new_task_stays_open_and_is_listed_by_recover_with_its_path(self):
        tid = self.say('[work new | Half done | research]')
        self.touch(tid)
        self.assertIn('--path=' + str(self.repo), self.calls('claim')[0])
        self.update_db(dropped=[{'issueId': int(NEW), 'title': 'Half done'}])
        out = self.hook('recover', hook_event_name='SessionStart')
        self.assertIn(NEW, out['hookSpecificOutput']['additionalContext'])
        self.assertIn('--path=' + str(self.repo), self.calls('dropped')[0])
        self.assertEqual(self.dbs()['issues'][NEW]['state'], 'OPEN')
        self.assertTrue(self.dbs()['issues'][NEW]['temporary'])

    def test_no_hook_mode_completes_a_task_without_a_done_or_complete_line(self):
        tid = self.say('[work new | Keep me | research]')
        self.touch(tid)
        self.hook('prompt', prompt='next')
        self.hook('heartbeat', env={'DIBS_BLOCK_BEAT_SECONDS': '0'})
        for event in ('PreCompact', 'SessionEnd', 'Stop'):
            self.hook('checkpoint', hook_event_name=event)
        self.hook('stop', last_assistant_message='Plain reply.\nContinue in this session: more.')
        self.hook('recover', hook_event_name='SessionStart')
        self.assertEqual(self.calls('complete'), [])
        self.assert_made_from_line('Keep me')
        self.assertEqual(self.dbs()['issues'][NEW]['state'], 'OPEN')
