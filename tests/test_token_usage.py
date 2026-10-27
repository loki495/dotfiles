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


class CostTests(unittest.TestCase):
    def test_sonnet_rates(self):
        # 1M in at $2, 1M out at $10, 1M cache read at $0.20, 1M cache write at 1.25 x $2
        self.assertAlmostEqual(tu.cost('claude-sonnet-5-5', 1e6, 1e6, 1e6, 1e6), 2 + 10 + 0.2 + 2.5)

    def test_longest_prefix_wins(self):
        self.assertEqual(tu.cost('claude-opus-5-5', 1e6, 0, 0, 0), 4)
        self.assertEqual(tu.cost('claude-opus-5-20260101', 1e6, 0, 0, 0), 5)

    def test_unknown_model_is_free(self):
        self.assertEqual(tu.cost('<synthetic>', 1e6, 1e6, 1e6, 1e6), 0)
        self.assertEqual(tu.cost('', 1e6, 0, 0, 0), 0)

    def test_bucket_cost_counts_a_deduped_turn_once(self):
        e = json.loads(entry('m1', 1_000_000))
        e['message']['model'] = 'claude-sonnet-5-5'
        e['message']['usage'].update(input_tokens=1_000_000, cache_creation_input_tokens=1_000_000)
        early = dict(e, message=dict(e['message'], usage=dict(e['message']['usage'], output_tokens=5)))
        with tempfile.TemporaryDirectory() as d:
            p = Path(d, 'proj')
            p.mkdir()
            (p / 's.jsonl').write_text('\n'.join(json.dumps(x) for x in (early, e)))
            turns = list(tu.read_turns(d, SINCE))
        b = next(iter(tu.aggregate(turns, lambda ts: 'x', 250_000).values()))
        self.assertAlmostEqual(b['cost'], 2 + 10 + 100 * 0.2 / 1e6 + 2.5)


class RunwayTests(unittest.TestCase):
    def test_runway_uses_average_per_active_day(self):
        text = tu.runway({'a': {'cost': 4.0}, 'b': {'cost': 6.0}, 'c': {'cost': 0.0}}, [10])
        self.assertIn('2 active days, $5.00/active day', text)
        self.assertIn('$10 prepaid lasts ~2.0 days', text)

    def test_runway_without_usage(self):
        self.assertIn('no priced usage', tu.runway({}, [10]))


if __name__ == '__main__':
    unittest.main()
