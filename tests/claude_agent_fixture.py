"""Give hook fixtures a known, live Claude ancestor regardless of test runner."""
import ctypes
from pathlib import Path


def use_test_process_as_claude(test):
    libc = ctypes.CDLL(None, use_errno=True)
    original = Path('/proc/self/comm').read_bytes().rstrip(b'\n')

    def rename(name):
        if libc.prctl(15, ctypes.c_char_p(name), 0, 0, 0) != 0:  # PR_SET_NAME
            raise OSError(ctypes.get_errno(), 'prctl(PR_SET_NAME) failed')

    rename(b'claude')
    test.addCleanup(rename, original)
