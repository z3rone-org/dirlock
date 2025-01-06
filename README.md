# Dirlock

[![PyPi badge](https://img.shields.io/pypi/v/dirlock)](https://pypi.org/project/dirlock/)
![pytest badge](https://github.com/z3rone-org/dirlock/actions/workflows/python-test.yml/badge.svg)

A simple directory-based lock implementation for Python. This package provides a lightweight and effective way
to coordinate access to shared resources using a lock directory mechanism.
This does not require any file locking capabilities of the underlying filesystem or network share.

## Installation

Install the package via pip:

```bash
pip install dirlock
```

## Usage

You can use the `DirLock` class to acquire and release locks in your Python code. The class also supports usage within a `with` clause for convenience.

### Example: Using the Lock Explicitly

```python
import time
from dirlock import DirLock

lock_dir_path = "/tmp/mylockdir.lock"
lock = DirLock(lock_dir_path)

print("Acquire lock...")
lock.acquire()
print("Lock acquired!")

# Perform critical section tasks here
# Simulating work
time.sleep(5)

# Release the lock
lock.release()
print("Lock released.")
```

### Example: Using the Lock in a `with` Clause

```python
import time
from dirlock import DirLock

lock_dir_path = "/tmp/mylockdir.lock"

with DirLock(lock_dir_path) as lock:
    print("Lock acquired!")
    # Perform critical section tasks
    time.sleep(5)  # Simulate work
    print("Work done!")

# The lock is automatically released when the block exits.
print("Lock released.")
```

## Parameters

- `lock_dir` (str): The path to the lock directory.
- `retry_interval` (float, default=0.1): Time to wait before retrying if the lock cannot be acquired.
- `timeout_interval` (float, default=-1): Timeout for acquiring lock. Set to negative value for no timeout.

## Change Default Values
You can change the default value for  `retry_interval`
via `DirLock.retry_interval=<new_value>`.

## License

This package is licensed under the MIT License.

