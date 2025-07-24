import os
import signal
import subprocess
import sys
import time
from unittest.mock import patch, MagicMock
from dirlock import DirLock, LockTimeoutException, _allActiveLocks, _clean_locks


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


def test_clean_locks_function(tmpdir):
    """Test that _clean_locks properly releases all active locks."""
    lockdir1 = os.path.join(tmpdir, '.lock1')
    lockdir2 = os.path.join(tmpdir, '.lock2')

    lock1 = DirLock(lockdir1)
    lock2 = DirLock(lockdir2)

    # Acquire both locks
    lock1.acquire()
    lock2.acquire()

    assert lock1.acquired
    assert lock2.acquired
    assert os.path.exists(lockdir1)
    assert os.path.exists(lockdir2)
    assert len(_allActiveLocks) == 2

    # Call _clean_locks to release all
    _clean_locks()

    # Verify all locks are released
    assert not lock1.acquired
    assert not lock2.acquired
    assert not os.path.exists(lockdir1)
    assert not os.path.exists(lockdir2)
    assert len(_allActiveLocks) == 0


def test_signal_handlers_mock(tmpdir):
    """Test signal handlers using mocks."""
    from dirlock import handle_sigint_cleanup, handle_sigterm_cleanup

    lockdir = os.path.join(tmpdir, '.lock')
    lock = DirLock(lockdir)
    lock.acquire()

    assert lock.acquired
    assert os.path.exists(lockdir)
    assert len(_allActiveLocks) == 1

    # Mock the original signal handler
    mock_handler = MagicMock()

    # Test SIGINT handler
    with patch('dirlock.original_sigint_handler', mock_handler):
        handle_sigint_cleanup(signal.SIGINT, None)
        mock_handler.assert_called_once_with(signal.SIGINT, None)

    # Verify lock was cleaned up
    assert not lock.acquired
    assert not os.path.exists(lockdir)
    assert len(_allActiveLocks) == 0

    # Test SIGTERM handler
    lock.acquire()  # Re-acquire for second test
    assert lock.acquired
    assert len(_allActiveLocks) == 1

    mock_handler.reset_mock()
    with patch('dirlock.original_sigterm_handler', mock_handler):
        handle_sigterm_cleanup(signal.SIGTERM, None)
        mock_handler.assert_called_once_with(signal.SIGTERM, None)

    # Verify lock was cleaned up
    assert not lock.acquired
    assert len(_allActiveLocks) == 0


def test_signal_handlers_with_none_original(tmpdir):
    """Test signal handlers when original handlers are None."""
    from dirlock import handle_sigint_cleanup, handle_sigterm_cleanup

    lockdir = os.path.join(tmpdir, '.lock')
    lock = DirLock(lockdir)
    lock.acquire()

    assert lock.acquired
    assert len(_allActiveLocks) == 1

    # Test with None original handlers (should not raise exception)
    with patch('dirlock.original_sigint_handler', None):
        handle_sigint_cleanup(signal.SIGINT, None)

    assert not lock.acquired
    assert len(_allActiveLocks) == 0

    # Test SIGTERM with None
    lock.acquire()
    assert len(_allActiveLocks) == 1

    with patch('dirlock.original_sigterm_handler', None):
        handle_sigterm_cleanup(signal.SIGTERM, None)

    assert not lock.acquired
    assert len(_allActiveLocks) == 0


def test_atexit_integration(tmpdir):
    """Test atexit integration using subprocess."""
    # Create a test script that uses DirLock and exits normally
    test_script = f'''
import os
import sys
sys.path.insert(0, "{os.path.dirname(os.path.dirname(__file__))}")
from dirlock import DirLock

lockdir = "{os.path.join(tmpdir, '.lock')}"
lock = DirLock(lockdir)
lock.acquire()

# Write a marker file to show the lock was acquired
with open("{os.path.join(tmpdir, 'acquired')}", "w") as f:
    f.write("locked")

# Exit normally - atexit should clean up the lock
'''

    script_path = os.path.join(tmpdir, 'test_script.py')
    with open(script_path, 'w') as f:
        f.write(test_script)

    # Run the script
    result = subprocess.run([sys.executable, script_path],
                            capture_output=True, text=True)

    # Check that script ran successfully
    assert result.returncode == 0, f"Script failed: {result.stderr}"

    # Check that the lock was acquired
    assert os.path.exists(os.path.join(tmpdir, 'acquired'))

    # Check that the lock was cleaned up on exit
    assert not os.path.exists(os.path.join(tmpdir, '.lock'))


def test_signal_integration_sigterm(tmpdir):
    """Test SIGTERM signal handling using subprocess."""
    # Create a test script that uses DirLock and receives SIGTERM
    test_script = f'''
import os
import sys
import signal
import time
sys.path.insert(0, "{os.path.dirname(os.path.dirname(__file__))}")
from dirlock import DirLock

lockdir = "{os.path.join(tmpdir, '.lock')}"
lock = DirLock(lockdir)
lock.acquire()

# Write a marker file to show the lock was acquired
with open("{os.path.join(tmpdir, 'acquired')}", "w") as f:
    f.write("locked")

# Wait for signal
try:
    time.sleep(10)  # Will be interrupted by SIGTERM
except KeyboardInterrupt:
    pass
'''

    script_path = os.path.join(tmpdir, 'test_script.py')
    with open(script_path, 'w') as f:
        f.write(test_script)

    # Run the script in background
    process = subprocess.Popen([sys.executable, script_path])

    # Give it time to acquire the lock
    time.sleep(0.5)

    # Check that the lock was acquired
    assert os.path.exists(os.path.join(tmpdir, 'acquired'))
    assert os.path.exists(os.path.join(tmpdir, '.lock'))

    # Send SIGTERM
    process.terminate()
    process.wait(timeout=5)

    # Check that the lock was cleaned up after SIGTERM
    assert not os.path.exists(os.path.join(tmpdir, '.lock'))


def test_multiple_locks_cleanup(tmpdir):
    """Test that multiple locks are properly cleaned up."""
    locks = []
    lockdirs = []

    # Create multiple locks
    for i in range(5):
        lockdir = os.path.join(tmpdir, f'.lock{i}')
        lock = DirLock(lockdir)
        lock.acquire()
        locks.append(lock)
        lockdirs.append(lockdir)

    # Verify all locks are acquired
    assert len(_allActiveLocks) == 5
    for lock in locks:
        assert lock.acquired
    for lockdir in lockdirs:
        assert os.path.exists(lockdir)

    # Clean all locks
    _clean_locks()

    # Verify all locks are released
    assert len(_allActiveLocks) == 0
    for lock in locks:
        assert not lock.acquired
    for lockdir in lockdirs:
        assert not os.path.exists(lockdir)
