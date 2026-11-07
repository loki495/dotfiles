"""Parse claim JSON even when the CLI appends a liveness notice."""
import importlib.machinery
import importlib.util
from pathlib import Path
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / 'ai' / 'scripts' / 'dibs-measure.py'


class DibsJsonClaimTest(unittest.TestCase):
    def setUp(self):
        loader = importlib.machinery.SourceFileLoader('claim_dm', str(SCRIPT))
        self.dm = importlib.util.module_from_spec(importlib.util.spec_from_loader('claim_dm', loader))
        loader.exec_module(self.dm)

    def test_claim_json_with_trailing_notice_preserves_capability_token(self):
        response = mock.Mock(returncode=0, stderr='', stdout='{"capability_token":"secret-token"}\nNote: process liveness could not be verified in this environment (weaker-assurance claim).\n')
        with mock.patch.object(self.dm.subprocess, 'run', return_value=response):
            result = self.dm.dibs_json('todo:agent:claim', '10')
        self.assertEqual(result['capability_token'], 'secret-token')

    def test_malformed_prefix_is_rejected(self):
        response = mock.Mock(returncode=0, stderr='', stdout='garbage\n{"capability_token":"secret-token"}\n')
        with mock.patch.object(self.dm.subprocess, 'run', return_value=response):
            with self.assertRaises(ValueError):
                self.dm.dibs_json('todo:agent:claim', '10')

    def test_unknown_trailing_output_is_rejected(self):
        response = mock.Mock(returncode=0, stderr='', stdout='{"capability_token":"secret-token"}\nunexpected error\n')
        with mock.patch.object(self.dm.subprocess, 'run', return_value=response):
            with self.assertRaises(ValueError):
                self.dm.dibs_json('todo:agent:claim', '10')


if __name__ == '__main__':
    unittest.main()
