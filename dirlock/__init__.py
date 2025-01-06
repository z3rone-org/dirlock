import os
import time
from datetime import datetime


class DirLock:
    default_retry_interval: float = 0.1
    def __init__(self,
                 lock_dir: str,
                 retry_interval: float = None,
                 timeout_interval: float = -1):
        """
        Initialize the DirLock.

        Args:
            lock_dir (str): Path to the lock directory.
            retry_interval (float): Time to wait before retrying (in seconds).
            timeout_interval (float): Timeout
        """
        self.lock_dir = str(lock_dir)
        self.timeout_interval = timeout_interval

        if retry_interval is None:
            self.retry_interval = DirLock.default_retry_interval
        else:
            self.retry_interval = retry_interval
        self.acquired = False

    def acquire(self):
        """
        Acquire the lock by following the directory-based lock mechanism.
        """
        start_time = datetime.now()

        while True:
            try:
                os.mkdir(self.lock_dir)
                self.acquired = True
                break
            except FileExistsError:
                pass

            if self.timeout_interval >= 0.0:
                if (datetime.now() - start_time).total_seconds() > self.timeout_interval:
                    raise LockTimeoutException()

            # If the lock directory exists, retry
            time.sleep(self.retry_interval)

    def release(self):
        """
        Release the lock if it is held by this instance.
        """
        try:
            os.rmdir(self.lock_dir)
        except FileNotFoundError:
            pass
        self.acquired = False

    def __enter__(self):
        """
        Context management entry point.
        """
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Context management exit point.
        """
        self.release()

class LockTimeoutException(Exception):
    def __init__(self, message="acquiring lock timed out"):
        super().__init__(message)