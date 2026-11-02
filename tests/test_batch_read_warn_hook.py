"""ai/hooks/batch-read-warn.py: warns on a repeated single-id todo_show/todo_claim_status, never blocks."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

HOOK = Path(__file__).resolve().parents[1] / 'ai' / 'hooks' / 'batch-read-warn.py'


def call(name, **inp):
    return {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'name': name, 'input': inp}]}}


USER = {'type': 'user', 'message': {'content': 'next'}}
RESULT = {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'content': 'x'}]}}


def run(entries, name='mcp__dibs__todo_show', tool_input=None, env=None):
    with tempfile.TemporaryDirectory() as tmp:
        transcript = Path(tmp) / 't.jsonl'
        transcript.write_text('\n'.join(json.dumps(e) for e in entries) + '\n')
        payload = {'tool_name': name, 'tool_input': tool_input or {'id': 2}, 'transcript_path': str(transcript)}
        proc = subprocess.run([str(HOOK)], input=json.dumps(payload), capture_output=True, text=True, env={**os.environ, **(env or {})})
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


class BatchReadWarnTest(unittest.TestCase):
    def test_first_single_call_is_silent(self):
        self.assertEqual(run([USER]), '')

    def test_second_single_call_without_user_turn_warns(self):
        out = run([USER, call('mcp__dibs__todo_show', id=1), RESULT])
        self.assertIn('ids', json.loads(out)['hookSpecificOutput']['additionalContext'])
        self.assertNotIn('permissionDecision', out)

    def test_user_turn_resets(self):
        self.assertEqual(run([call('mcp__dibs__todo_show', id=1), RESULT, USER]), '')

    def test_batch_forms_are_never_warned_or_counted(self):
        self.assertEqual(run([USER, call('mcp__dibs__todo_show', id=1)], tool_input={'ids': [1, 2]}), '')
        self.assertEqual(run([USER, call('mcp__dibs__todo_show', ids=[1, 2]), RESULT]), '')

    def test_claim_status_and_off_switch(self):
        entries = [USER, call('mcp__dibs__todo_claim_status', issueId=1), RESULT]
        self.assertIn('issueIds', run(entries, 'mcp__dibs__todo_claim_status', {'issueId': 2}))
        self.assertEqual(run(entries, 'mcp__dibs__todo_claim_status', {'issueId': 2}, {'BATCH_READ_WARN': 'off'}), '')

    def test_missing_transcript_is_silent(self):
        proc = subprocess.run([str(HOOK)], input=json.dumps({'tool_name': 'mcp__dibs__todo_show', 'tool_input': {'id': 1}}),
                              capture_output=True, text=True)
        self.assertEqual((proc.returncode, proc.stdout), (0, ''))


if __name__ == '__main__':
    unittest.main()
