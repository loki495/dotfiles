"""ai/scripts/token-usage.py: dedupe, bucketing, malformed lines."""
import datetime
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'ai' / 'scripts' / 'token-usage.py'
loader = importlib.machinery.SourceFileLoader('token_usage', str(SCRIPT))
spec = importlib.util.spec_from_loader('token_usage', loader)
tu = importlib.util.module_from_spec(spec)
loader.exec_module(tu)

NOW = datetime.datetime.now(datetime.timezone.utc)
SINCE = NOW - datetime.timedelta(days=7)


def entry(mid, out, read=100, ts=None):
    return json.dumps({'type': 'assistant', 'timestamp': (ts or NOW).isoformat(),
                       'message': {'id': mid, 'usage': {'input_tokens': 1, 'cache_read_input_tokens': read,
                                                        'cache_creation_input_tokens': 0, 'output_tokens': out}}})


class TokenUsageTests(unittest.TestCase):
    def run_lines(self, lines, sub='s1.jsonl'):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d, 'proj')
            p.mkdir()
            (p / sub).write_text('\n'.join(lines))
            return list(tu.read_turns(d, SINCE))

    def test_dedupes_by_message_id_keeping_final_output(self):
        turns = self.run_lines([entry('m1', 5), entry('m1', 50), entry('m2', 7)])
        self.assertEqual(sorted(t[5] for t in turns), [7, 50])

    def test_skips_malformed_and_old_lines(self):
        old = NOW - datetime.timedelta(days=30)
        turns = self.run_lines(['{broken', '{"type":"assistant"}', entry('m1', 5, ts=old), entry('m2', 5)])
        self.assertEqual(len(turns), 1)

    def test_aggregate_counts_turns_over_limit(self):
        turns = self.run_lines([entry('m1', 5, read=500), entry('m2', 5, read=10)])
        b = next(iter(tu.aggregate(turns, lambda ts: 'x', 100).values()))
        self.assertEqual((b['turns'], b['over'], len(b['sessions'])), (2, 1, 1))

    def test_render_empty(self):
        self.assertIn('no transcripts', tu.render('t', {}))


if __name__ == '__main__':
    unittest.main()
