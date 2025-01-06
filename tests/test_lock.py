from datetime import datetime
import os
from dirlock import DirLock, LockTimeoutException


def test_two_locks(tmpdir):
    lockdir = os.path.join(tmpdir, '.lock')
    lock1 = DirLock(lockdir)
    lock2 = DirLock(lockdir)

    assert not lock1.acquired
    assert not lock2.acquired

    # Acquire the lock
    lock1.acquire()

    assert lock1.acquired
    assert not lock2.acquired

    lock1.release()
    lock2.acquire()

    assert not lock1.acquired
    assert lock2.acquired

    lock2.release()

    assert not lock1.acquired
    assert not lock2.acquired


def test_timeout(tmpdir):
    lockdir = os.path.join(tmpdir, '.lock')
    lock1 = DirLock(lockdir)
    lock2 = DirLock(lockdir, timeout_interval=3)

    lock1.acquire()
    assert lock1.acquired

    try:
        lock2.acquire()
        assert False
    except LockTimeoutException:
        assert not lock2.acquired

    lock1.release()
    assert not lock1.acquired
    assert not lock2.acquired


def test_context_manager(tmpdir):
    lockdir = os.path.join(tmpdir, '.lock')
    lock = DirLock(str(lockdir))

    # Use the context manager to acquire and release the lock
    with lock:
        # Check that the lock directory was created with the correct UUID
        assert os.path.exists(str(lockdir))

    # Ensure that the lock directory is removed after exiting the context
    assert not os.path.exists(str(lockdir))
