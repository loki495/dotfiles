"""ai/hooks/rule-inject.py: just-in-time rule injection, once per context lifetime."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

HOOK = Path(__file__).resolve().parents[1] / 'ai' / 'hooks' / 'rule-inject.py'
EXPORT = """<!-- generated -->

## 732@1 Rule: docs and tests
TEXT-732
## 737@1 Rule: no dibs refs
TEXT-737
## 738@1 Rule: no trailer
TEXT-738
## 734@1 Rule: push
TEXT-734
## 735@1 Rule: force
TEXT-735
## 730@1 Rule: done
TEXT-730
## 740@1 Rule: sad paths
TEXT-740
## 928@1 Rule: peer
TEXT-928
## 929@1 Rule: stale
TEXT-929
"""
PRIVATE = "## 745@2 Rule: home\nTEXT-745-PRIVATE\n"


class RuleInjectTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: subprocess.run(['rm', '-rf', str(self.tmp)]))
        (self.tmp / 'rules.md').write_text(EXPORT)
        (self.tmp / 'private.md').write_text(PRIVATE)
        self.env = {**os.environ, 'RULE_FILES': f"{self.tmp / 'rules.md'}:{self.tmp / 'private.md'}",
                    'RULE_STATE_DIR': str(self.tmp / 'state')}

    def run_hook(self, raw=None, env=None, **event):
        event.setdefault('session_id', 's1')
        proc = subprocess.run([str(HOOK)], input=raw if raw is not None else json.dumps(event),
                              capture_output=True, text=True, env=env or self.env)
        self.assertEqual((proc.returncode, proc.stderr), (0, ''))
        return json.loads(proc.stdout)['hookSpecificOutput'] if proc.stdout.strip() else None

    def bash(self, cmd, **kw):
        return self.run_hook(hook_event_name='PreToolUse', tool_name='Bash', tool_input={'command': cmd}, **kw)

    def test_commit_is_denied_once_with_its_rules_then_proceeds(self):
        out = self.bash('git commit -m x')
        self.assertEqual(out['permissionDecision'], 'deny')
        for i in (732, 737, 738):
            self.assertIn(f'TEXT-{i}', out['permissionDecisionReason'])
        self.assertIsNone(self.bash('git commit -m again'))

    def test_push_through_rtk_and_chained_is_denied_once(self):
        out = self.bash('cd x && rtk git push origin master')
        self.assertEqual(out['permissionDecision'], 'deny')
        self.assertIn('TEXT-734', out['permissionDecisionReason'])
        self.assertIsNone(self.bash('git push'))

    def test_non_deny_events_use_additional_context(self):
        out = self.bash('mysql -e "select 1"')
        self.assertEqual((out['hookEventName'], 'TEXT-929' in out['additionalContext']), ('PreToolUse', True))
        self.assertNotIn('permissionDecision', out)

    def test_test_file_edit_injects_test_rule(self):
        out = self.run_hook(hook_event_name='PreToolUse', tool_name='Edit',
                            tool_input={'file_path': '/x/tests/FooTest.php'})
        self.assertIn('TEXT-740', out['additionalContext'])

    def test_private_export_is_read(self):
        out = self.bash('curl http://x')
        self.assertIn('TEXT-745-PRIVATE', out['additionalContext'])

    def test_the_first_definition_of_an_id_wins_across_files(self):
        (self.tmp / 'private.md').write_text('## 732@1 Rule: override\nTEXT-EVIL\n')
        out = self.bash('git commit -m x')
        self.assertIn('TEXT-732', out['permissionDecisionReason'])
        self.assertNotIn('TEXT-EVIL', out['permissionDecisionReason'])

    def test_a_revision_bump_resends(self):
        self.assertIsNotNone(self.bash('git commit -m x'))
        self.assertIsNone(self.bash('git commit -m x'))
        (self.tmp / 'rules.md').write_text(EXPORT.replace('732@1', '732@2'))
        out = self.bash('git commit -m x')
        self.assertIn('TEXT-732', out['permissionDecisionReason'])
        self.assertNotIn('TEXT-737', out['permissionDecisionReason'])

    def test_compact_clear_resume_empty_the_set_and_startup_does_not(self):
        for source in ('compact', 'clear', 'resume'):
            self.bash('git commit -m x')
            out = self.run_hook(hook_event_name='SessionStart', source=source)
            self.assertIn('contextReset: true', out['additionalContext'])
            self.assertIsNotNone(self.bash('git commit -m x'), source)
        self.bash('git commit -m x')
        self.assertIsNone(self.run_hook(hook_event_name='SessionStart', source='startup'))
        self.assertIsNone(self.bash('git commit -m x'))

    def test_sets_are_per_session_and_per_subagent(self):
        self.bash('git commit -m x')
        self.assertIsNotNone(self.bash('git commit -m x', agent_id='a1'))
        self.assertIsNone(self.bash('git commit -m x', agent_id='a1'))
        self.assertIsNotNone(self.bash('git commit -m x', session_id='s2'))

    def test_todo_claim_response_marks_rules_delivered(self):
        wo = {'workOrder': {'rules': [{'id': 732, 'revision': 1, 'text': 'x'}, {'id': 737, 'revision': 1}]}}
        for resp in (wo, json.dumps(wo), [{'type': 'text', 'text': json.dumps(wo)}]):
            self.run_hook(hook_event_name='PostToolUse', tool_name='mcp__dibs__todo_claim', tool_response=resp,
                          session_id='c' + str(type(resp)))
        out = self.bash('git commit -m x', session_id="c<class 'dict'>")
        self.assertNotIn('TEXT-732', out['permissionDecisionReason'])  # delivered by Dibs
        self.assertIn('TEXT-737', out['permissionDecisionReason'])  # sent without text: still ours

    def test_peer_prompt_and_other_tools(self):
        self.assertIsNone(self.run_hook(hook_event_name='UserPromptSubmit', prompt='hello'))
        out = self.run_hook(hook_event_name='UserPromptSubmit', prompt='[sessioneer peer: a · /x · master] hi')
        self.assertIn('TEXT-928', out['additionalContext'])
        self.assertIsNone(self.run_hook(hook_event_name='PreToolUse', tool_name='Read', tool_input={}))

    # sad paths: never a crash, never output
    def test_missing_export_is_silent(self):
        env = {**self.env, 'RULE_FILES': str(self.tmp / 'nope.md')}
        self.assertIsNone(self.run_hook(env=env, hook_event_name='PreToolUse', tool_name='Bash',
                                        tool_input={'command': 'git commit'}))

    def test_malformed_input_and_unknown_event_are_silent(self):
        for raw in ('', 'not json', '[]', '{"session_id": 3}', json.dumps({'session_id': 's', 'hook_event_name': 'Weird'})):
            self.assertIsNone(self.run_hook(raw=raw), raw)

    def test_malformed_export_is_silent(self):
        (self.tmp / 'rules.md').write_text('\x00garbage\n## x@y z\n')
        self.assertIsNone(self.bash('git commit -m x'))


if __name__ == '__main__':
    unittest.main()
