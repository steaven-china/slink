import os
import tempfile
import unittest

from slink.lock import FileLock


class TestLock(unittest.TestCase):
    def test_acquire_release(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "lockfile")
            lock = FileLock(path)
            lock.acquire()
            self.assertTrue(os.path.exists(path))
            lock.release()

    def test_context_manager(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "lockfile")
            with FileLock(path) as lock:
                self.assertTrue(os.path.exists(path))
                self.assertIsNotNone(lock._fd)


if __name__ == "__main__":
    unittest.main()
