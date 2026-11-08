"""The mandatory worker-persona rule reaches agent-launching tool calls."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

HOOK = Path(__file__).resolve().parents[1] / 'ai/hooks/rule-inject.py'
RULE_TEXT = 'MANDATORY-PERSONA: Every delegated worker must use its assigned persona.'
EXPORT = f'## 1468@1 Rule: mandatory worker persona\n{RULE_TEXT}\n'


class PersonaRuleHookTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        rules = root / 'rules.md'
        rules.write_text(EXPORT)
        (root / 'trig.json').write_text(json.dumps({'agent-launch': [1468]}))
        self.env = {**os.environ, 'RULE_FILES': str(rules), 'RULE_STATE_DIR': str(root / 'state'),
                    'RULE_TRIGGERS': str(root / 'trig.json'), 'RULE_PRIVATE_KEYS': str(root / 'nokeys.json'),
                    'SESSIONEER_BIN': str(root / 'no-such-sessioneer'), 'HOME': str(root)}

    def hook(self, **event):
        event.setdefault('session_id', 'persona-session')
        proc = subprocess.run([str(HOOK)], input=json.dumps(event), capture_output=True,
                              text=True, env=self.env)
        self.assertEqual((proc.returncode, proc.stderr), (0, ''))
        return json.loads(proc.stdout)['hookSpecificOutput'] if proc.stdout.strip() else None

    def launch(self, tool, **kwargs):
        return self.hook(hook_event_name='PreToolUse', tool_name=tool,
                         tool_input={'prompt': 'Implement the assigned task'}, **kwargs)

    def assert_injected(self, output):
        self.assertIsNotNone(output)
        self.assertEqual(output['hookEventName'], 'PreToolUse')
        self.assertIn(RULE_TEXT, output['additionalContext'])
        self.assertEqual(output['additionalContext'].count(RULE_TEXT), 1)

    def test_agent_and_task_each_inject_in_fresh_context(self):
        for tool in ('Agent', 'Task'):
            with self.subTest(tool=tool):
                self.assert_injected(self.launch(tool, session_id=f'session-{tool}'))
                self.assertIsNone(self.launch(tool, session_id=f'session-{tool}'))

    def test_rule_is_shared_within_context_and_reinjected_after_reset(self):
        self.assert_injected(self.launch('Agent'))
        self.assertIsNone(self.launch('Task'))
        self.assertIsNone(self.hook(hook_event_name='SessionStart', source='startup'))
        self.assertIsNone(self.launch('Agent'))
        for source in ('compact', 'clear', 'resume'):
            with self.subTest(source=source):
                reset = self.hook(hook_event_name='SessionStart', source=source)
                self.assertIn('contextReset: true', reset['additionalContext'])
                self.assert_injected(self.launch('Task'))
                self.assertIsNone(self.launch('Agent'))

    def test_subagent_context_is_independent(self):
        self.assert_injected(self.launch('Agent'))
        self.assert_injected(self.launch('Task', agent_id='child-1'))
        self.assertIsNone(self.launch('Agent', agent_id='child-1'))


if __name__ == '__main__':
    unittest.main()
