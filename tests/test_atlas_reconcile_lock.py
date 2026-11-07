"""Cross-process exclusion around refresh and reconciler's state scan."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
CHILD = r'''
import importlib.machinery, importlib.util, os, pathlib, sys, time
root, role, marker = pathlib.Path(sys.argv[1]), sys.argv[2], pathlib.Path(sys.argv[3])
name = 'atlas-refresh.py' if role.startswith('refresh') else 'dibs-reconcile.py'
loader = importlib.machinery.SourceFileLoader('worker', str(root / 'ai/scripts' / name))
mod = importlib.util.module_from_spec(importlib.util.spec_from_loader('worker', loader))
loader.exec_module(mod)
def work(*args, **kwargs):
    marker.write_text('entered')
    if role.endswith('hold'):
        deadline = time.monotonic() + 4
        while not (marker.parent / 'release').exists() and time.monotonic() < deadline:
            time.sleep(0.01)
    raise RuntimeError('controlled stop')
try:
    if role.startswith('refresh'):
        mod.run_locked = work
        mod.run(False)
    else:
        mod.gather = work
        mod.reconcile()
except RuntimeError:
    pass
'''


class ReconcilerLockTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = {**os.environ, 'ATLAS_RECONCILE_LOCK': str(self.root / 'shared.lock'),
                    'ATLAS_QUEUE': str(self.root / 'queue'), 'DIBS_ATLAS_HINTS': str(self.root / 'hints')}
        self.processes = []
        self.addCleanup(self.stop_processes)

    def stop_processes(self):
        for process in self.processes:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=3)

    def spawn(self, role, marker):
        proc = subprocess.Popen([sys.executable, '-c', CHILD, str(ROOT), role, str(marker)],
                                env=self.env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.processes.append(proc)
        return proc

    def wait_for(self, marker):
        deadline = time.monotonic() + 3
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(marker.exists(), f'{marker} not reached')

    def test_both_scripts_serialize_while_other_owns_lock(self):
        for holder, contender in [('refresh_hold', 'reconcile_try'), ('reconcile_hold', 'refresh_try')]:
            with self.subTest(holder=holder):
                for name in ('release', 'holder', 'contender'):
                    (self.root / name).unlink(missing_ok=True)
                first = self.spawn(holder, self.root / 'holder')
                self.wait_for(self.root / 'holder')
                second = self.spawn(contender, self.root / 'contender')
                time.sleep(0.25)
                self.assertFalse((self.root / 'contender').exists(), 'contender entered while lock held')
                (self.root / 'release').touch()
                first.wait(timeout=3)
                second.wait(timeout=3)
                self.assertEqual(first.returncode, 0)
                self.assertEqual(second.returncode, 0)
                self.assertTrue((self.root / 'contender').exists())

    def test_exception_releases_shared_lock(self):
        first = self.spawn('refresh_try', self.root / 'first')
        first.wait(timeout=3)
        self.assertEqual(first.returncode, 0)
        second = self.spawn('reconcile_try', self.root / 'second')
        second.wait(timeout=3)
        self.assertEqual(second.returncode, 0)
        self.assertTrue((self.root / 'second').exists())


if __name__ == '__main__':
    unittest.main()
