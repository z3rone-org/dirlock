import os
import time
import atexit
from datetime import datetime


# keep a list of currently acquired looks
# so these can be cleaned up on exit
_allActiveLocks = set()

# function to clean up all active locks
def _clean_locks():
    global _allActiveLock
    for dl in _allActiveLock:
        dl.release()

# we don't want to call the original handler
original_sigint_handler = signal.getsignal(signal.SIGINT)
original_sigterm_handler = signal.getsignal(signal.SIGTERM)

def handle_sigint_cleanup(signum, frame):
    global original_sigint_handler
    _clean_locks()
    if original_sigint_handler is not None:
        original_sigint_handler()

def handle_sigterm_cleanup(signum, frame):
    global original_sigterm_handler
    _clean_locks()
    if original_sigterm_handler is not None:
        original_sigterm_handler()

# normal exit clean up
atexit.register(cleanlocks)

# ctrl+c cleanup
signal.signal(signal.SIGINT, handle_sigint_cleanup)
# sigterm cleanup
signal.signal(signal.SIGTERM, handle_sigterm_cleanup)


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
        global _allActiveLock
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
        global _allActiveLock
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
