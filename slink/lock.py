"""
Cross-platform advisory file locking for the slink store.
"""
import os
import sys


if sys.platform == "win32":
    import msvcrt

    class FileLock:
        def __init__(self, path: str):
            self.path = path
            self._fd = None

        def acquire(self):
            dir_path = os.path.dirname(self.path)
            if dir_path:
                os.makedirs(dir_path, mode=0o700, exist_ok=True)
            self._fd = os.open(self.path, os.O_CREAT | os.O_RDWR)
            os.chmod(self.path, 0o600)
            msvcrt.locking(self._fd, msvcrt.LK_LOCK, 1)

        def release(self):
            if self._fd is not None:
                try:
                    msvcrt.locking(self._fd, msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
                try:
                    os.close(self._fd)
                except OSError:
                    pass
                self._fd = None

        def __enter__(self):
            self.acquire()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.release()
            return False
else:
    import fcntl

    class FileLock:
        def __init__(self, path: str):
            self.path = path
            self._fd = None

        def acquire(self):
            dir_path = os.path.dirname(self.path)
            if dir_path:
                os.makedirs(dir_path, mode=0o700, exist_ok=True)
            self._fd = os.open(self.path, os.O_CREAT | os.O_RDWR)
            os.chmod(self.path, 0o600)
            fcntl.flock(self._fd, fcntl.LOCK_EX)

        def release(self):
            if self._fd is not None:
                try:
                    fcntl.flock(self._fd, fcntl.LOCK_UN)
                except OSError:
                    pass
                try:
                    os.close(self._fd)
                except OSError:
                    pass
                self._fd = None

        def __enter__(self):
            self.acquire()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.release()
            return False
