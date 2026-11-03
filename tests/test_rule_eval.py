"""ai/scripts/rule-eval.py: scenario table is well formed; the checker logic needs no model call."""
import importlib.machinery
import importlib.util
from pathlib import Path
import re
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'ai' / 'scripts' / 'rule-eval.py'
loader = importlib.machinery.SourceFileLoader('re_', str(SCRIPT))
mod = importlib.util.module_from_spec(importlib.util.spec_from_loader('re_', loader))
loader.exec_module(mod)


class RuleEvalTest(unittest.TestCase):
    def test_every_scenario_has_a_rule_a_prompt_and_a_valid_check(self):
        self.assertGreaterEqual(len(mod.SCENARIOS), 10)
        self.assertLessEqual(len(mod.SCENARIOS), 15)
        for rule, prompt, want, forbid in mod.SCENARIOS:
            self.assertTrue(rule.isdigit() and prompt)
            self.assertTrue(want or forbid)
            for rx in (want, forbid):
                if rx:
                    re.compile(rx)

    def test_status_line_pattern_accepts_the_five_phrases_only(self):
        for ok in ('Safe to archive this session.', 'Waiting on Andres: x', 'All planned work is done.'):
            self.assertTrue(re.search(mod.STATUS, ok))
        self.assertFalse(re.search(mod.STATUS, 'OK'))


if __name__ == '__main__':
    unittest.main()
