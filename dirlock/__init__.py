import os
import signal
import time
import atexit
from datetime import datetime
"""
This module provides a directory-based locking mechanism.
It allows for acquiring and releasing locks using directories,
which can be useful in scenarios where file-based based
operations can not be done atomically (e.g.
distributed or cluster filesystem)

The DirLock class provides methods to acquire and release locks,
and it supports context management for easy usage.

It also handles cleanup of locks on program exit or signal interrupts.
"""


# keep a list of currently acquired locks
# so these can be cleaned up on exit
_allActiveLocks = set()
# we don't want to call the original handler
original_sigint_handler = signal.getsignal(signal.SIGINT)
original_sigterm_handler = signal.getsignal(signal.SIGTERM)


# function to clean up all active locks
def _clean_locks():
    global _allActiveLocks
    # Create a copy to avoid "Set changed size during iteration" error
    locks_to_release = list(_allActiveLocks)
    for dl in locks_to_release:
        dl.release()
        _allActiveLocks.remove(dl)


def handle_sigint_cleanup(signum, frame):
    """
    Handle SIGINT (Ctrl+C) cleanup.
    This function is called when a SIGINT signal is received.
    It cleans up all active locks and calls the original signal handler if it exists.
    """
    global original_sigint_handler
    _clean_locks()
    if original_sigint_handler is not None:
        # restore the original handler 
        signal.signal(signal.SIGINT, original_sigint_handler)
        # and re-raise the signal
        os.kill(os.getpid(), signal.SIGINT)


def handle_sigterm_cleanup(signum, frame):
    """
    Handle SIGTERM cleanup.
    This function is called when a SIGTERM signal is received.
    It cleans up all active locks and calls the original signal handler if it exists.
    """
    global original_sigterm_handler
    _clean_locks()
    if original_sigterm_handler is not None:
        # restore the original handler 
        signal.signal(signal.SIGTERM, original_sigterm_handler)
        # and re-raise the signal
        os.kill(os.getpid(), signal.SIGTERM)


# normal exit clean up
atexit.register(_clean_locks)

try:
    # ctrl+c cleanup
    signal.signal(signal.SIGINT, handle_sigint_cleanup)
except Exception:
    pass

try:
    # sigterm cleanup
    signal.signal(signal.SIGTERM, handle_sigterm_cleanup)
except Exception:
    pass


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
        global _allActiveLocks
        start_time = datetime.now()

        while True:
            try:
                os.mkdir(self.lock_dir)
                self.acquired = True
                _allActiveLocks.add(self)
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
        if self.acquired:
            try:
                os.rmdir(self.lock_dir)
                _allActiveLocks.remove(self)
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

